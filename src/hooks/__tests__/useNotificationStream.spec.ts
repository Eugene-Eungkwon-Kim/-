import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from './renderHook';
import { useNotificationStream, type StreamLike } from '../useNotificationStream';
import * as client from '../../webApiClient';

/**
 * Phase 15 - B-2: 알림 스트림 훅.
 *
 * 이 기능의 위험은 전부 재연결과 정리 경로에 있다. happy-dom에는 EventSource가
 * 아예 없어(전역·window 모두 undefined) 훅이 생성 팩토리를 주입받도록 설계했고,
 * 여기서 가짜 스트림을 넣어 그 경로를 직접 검증한다.
 */

/** 테스트가 이벤트를 직접 밀어넣을 수 있는 가짜 EventSource */
class FakeStream implements StreamLike {
  static instances: FakeStream[] = [];

  readonly url: string;
  closed = false;
  onerror: ((event: unknown) => void) | null = null;
  private readonly listeners = new Map<string, ((event: { data?: string }) => void)[]>();

  constructor(url: string) {
    this.url = url;
    FakeStream.instances.push(this);
  }

  addEventListener(type: string, listener: (event: { data?: string }) => void): void {
    const existing = this.listeners.get(type) ?? [];
    existing.push(listener);
    this.listeners.set(type, existing);
  }

  emit(type: string, data?: string): void {
    for (const listener of this.listeners.get(type) ?? []) listener({ data });
  }

  fail(): void {
    this.onerror?.({});
  }

  close(): void {
    this.closed = true;
  }
}

const notification = (id: string, readAt: string | null = null): client.NotificationRecord => ({
  id,
  userId: 'u1',
  metric: 'creditScore',
  severity: 'warning',
  value: 580,
  threshold: 600,
  snapshotDate: '2026-01-01',
  readAt,
  createdAt: '2026-01-01 00:00:00'
});

describe('useNotificationStream', () => {
  let ticketCalls = 0;

  beforeEach(() => {
    vi.useFakeTimers();
    FakeStream.instances = [];
    ticketCalls = 0;

    vi.spyOn(client, 'getNotifications').mockResolvedValue({ success: true, data: [] });
    vi.spyOn(client, 'getUnreadCount').mockResolvedValue({ success: true, data: { count: 0 } });
    vi.spyOn(client, 'issueStreamTicket').mockImplementation(async () => {
      ticketCalls += 1;
      return { success: true, data: { ticket: `t${ticketCalls}`, expiresInMs: 60_000 } };
    });
    // 지터가 테스트 시간을 흔들지 않도록 고정한다.
    vi.spyOn(Math, 'random').mockReturnValue(0);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const factory = (url: string): StreamLike => new FakeStream(url);

  /** 마이크로태스크를 비워 훅 내부의 await가 진행되게 한다. */
  async function flush(): Promise<void> {
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
  }

  it('연결되면 발급받은 티켓으로 스트림을 열고 status가 open이 된다', async () => {
    const { result } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    expect(FakeStream.instances).toHaveLength(1);
    expect(FakeStream.instances[0].url).toContain('ticket=t1');

    await act(async () => FakeStream.instances[0].emit('connected'));
    expect(result.current.status).toBe('open');
  });

  it('userId가 null이면 스트림을 열지 않는다', async () => {
    renderHook(() => useNotificationStream(null, factory));
    await flush();

    expect(FakeStream.instances).toHaveLength(0);
    expect(ticketCalls).toBe(0);
  });

  it('notification 프레임을 받으면 목록 앞에 쌓이고 미읽음 수가 는다', async () => {
    const { result } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    await act(async () => {
      FakeStream.instances[0].emit('notification', JSON.stringify(notification('n1')));
      FakeStream.instances[0].emit('notification', JSON.stringify(notification('n2')));
    });

    expect(result.current.notifications.map((n) => n.id)).toEqual(['n2', 'n1']);
    expect(result.current.unreadCount).toBe(2);
  });

  it('깨진 프레임은 무시하고 스트림을 유지한다', async () => {
    const { result } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    await act(async () => FakeStream.instances[0].emit('notification', '{not json'));

    expect(result.current.notifications).toHaveLength(0);
    expect(FakeStream.instances[0].closed).toBe(false);
  });

  it('오류 시 close()를 불러 브라우저 자동 재연결을 차단한다', async () => {
    renderHook(() => useNotificationStream('u1', factory));
    await flush();

    await act(async () => FakeStream.instances[0].fail());

    // close()가 없으면 EventSource가 소진된 티켓으로 같은 URL에 계속 재접속한다.
    expect(FakeStream.instances[0].closed).toBe(true);
  });

  it('재연결 지연이 1s → 2s → 4s로 늘어난다', async () => {
    renderHook(() => useNotificationStream('u1', factory));
    await flush();

    await act(async () => FakeStream.instances[0].fail());
    await act(async () => void vi.advanceTimersByTime(999));
    expect(FakeStream.instances).toHaveLength(1); // 아직 1초가 안 됨

    await act(async () => void vi.advanceTimersByTime(1));
    await flush();
    expect(FakeStream.instances).toHaveLength(2);

    await act(async () => FakeStream.instances[1].fail());
    await act(async () => void vi.advanceTimersByTime(1999));
    expect(FakeStream.instances).toHaveLength(2);
    await act(async () => void vi.advanceTimersByTime(1));
    await flush();
    expect(FakeStream.instances).toHaveLength(3);

    await act(async () => FakeStream.instances[2].fail());
    await act(async () => void vi.advanceTimersByTime(3999));
    expect(FakeStream.instances).toHaveLength(3);
    await act(async () => void vi.advanceTimersByTime(1));
    await flush();
    expect(FakeStream.instances).toHaveLength(4);
  });

  it('연결에 성공하면 백오프가 초기화된다', async () => {
    renderHook(() => useNotificationStream('u1', factory));
    await flush();

    // 두 번 실패해 지연을 키운 뒤
    await act(async () => FakeStream.instances[0].fail());
    await act(async () => void vi.advanceTimersByTime(1000));
    await flush();
    await act(async () => FakeStream.instances[1].fail());
    await act(async () => void vi.advanceTimersByTime(2000));
    await flush();

    // 성공시키면
    await act(async () => FakeStream.instances[2].emit('connected'));

    // 다음 실패는 다시 1초여야 한다.
    await act(async () => FakeStream.instances[2].fail());
    await act(async () => void vi.advanceTimersByTime(1000));
    await flush();
    expect(FakeStream.instances).toHaveLength(4);
  });

  it('티켓 발급이 실패해도 같은 백오프로 물러난다', async () => {
    vi.mocked(client.issueStreamTicket).mockResolvedValue({
      success: false,
      error: { code: 'RATE_LIMITED', message: 'too many' }
    });

    const { result } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    expect(FakeStream.instances).toHaveLength(0);
    expect(result.current.status).toBe('retrying');
  });

  it('언마운트 후에는 재연결 타이머가 살아남지 않는다', async () => {
    const { unmount } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    await act(async () => FakeStream.instances[0].fail());
    const ticketsBefore = ticketCalls;

    unmount();
    await act(async () => void vi.advanceTimersByTime(60_000));
    await flush();

    // 타이머가 남아 있으면 사라진 컴포넌트가 계속 티켓을 발급한다.
    expect(ticketCalls).toBe(ticketsBefore);
    expect(FakeStream.instances).toHaveLength(1);
  });

  it('언마운트 시 열린 스트림을 닫는다', async () => {
    const { unmount } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    unmount();
    expect(FakeStream.instances[0].closed).toBe(true);
  });

  it('userId가 바뀌면 이전 스트림을 닫고 새로 연다', async () => {
    const { rerender } = renderHook(({ id }: { id: string }) => useNotificationStream(id, factory), {
      initialProps: { id: 'u1' }
    });
    await flush();

    rerender({ id: 'u2' });
    await flush();

    expect(FakeStream.instances[0].closed).toBe(true);
    expect(FakeStream.instances).toHaveLength(2);
  });

  it('강제 로그아웃 시 스트림을 닫고 status가 stopped가 된다', async () => {
    // notifyForcedLogout은 모듈 내부 함수라 외부에서 부를 수 없다. 훅이 등록하는
    // 콜백을 가로채 직접 호출해, 등록과 반응을 함께 검증한다.
    let forcedLogout: (() => void) | null = null;
    vi.spyOn(client, 'onForcedLogout').mockImplementation((callback) => {
      forcedLogout = callback;
      return () => {
        forcedLogout = null;
      };
    });

    const { result } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    // 열린 스트림은 재인증되지 않으므로, 닫지 않으면 로그아웃한 사용자에게
    // 알림이 계속 흐른다.
    expect(forcedLogout).not.toBeNull();
    await act(async () => forcedLogout!());

    expect(FakeStream.instances[0].closed).toBe(true);
    expect(result.current.status).toBe('stopped');
  });

  it('서버가 revoked를 보내면 재연결하지 않고 멈춘다', async () => {
    const { result } = renderHook(() => useNotificationStream('u1', factory));
    await flush();

    await act(async () => FakeStream.instances[0].emit('revoked', JSON.stringify({ reason: 'session_ended' })));

    expect(result.current.status).toBe('stopped');
    expect(FakeStream.instances[0].closed).toBe(true);

    // 취소 후에는 소켓이 닫히며 onerror가 뒤따를 수 있다. 그때도 재연결하면
    // 티켓이 아직 발급되는 짧은 창 동안 붙었다 끊기를 반복한다.
    await act(async () => FakeStream.instances[0].fail());
    await act(async () => void vi.advanceTimersByTime(60_000));
    await flush();

    expect(FakeStream.instances).toHaveLength(1);
  });

  describe('markRead', () => {
    it('성공하면 읽음으로 바뀌고 미읽음 수가 준다', async () => {
      vi.mocked(client.getNotifications).mockResolvedValue({ success: true, data: [notification('n1')] });
      vi.mocked(client.getUnreadCount).mockResolvedValue({ success: true, data: { count: 1 } });
      vi.spyOn(client, 'markNotificationRead').mockResolvedValue({
        success: true,
        data: notification('n1', '2026-01-02')
      });

      const { result } = renderHook(() => useNotificationStream('u1', factory));
      await flush();

      await act(async () => {
        await result.current.markRead('n1');
      });

      expect(result.current.notifications[0].readAt).not.toBeNull();
      expect(result.current.unreadCount).toBe(0);
    });

    it('실패하면 낙관적 갱신을 되돌린다', async () => {
      vi.mocked(client.getNotifications).mockResolvedValue({ success: true, data: [notification('n1')] });
      vi.mocked(client.getUnreadCount).mockResolvedValue({ success: true, data: { count: 1 } });
      vi.spyOn(client, 'markNotificationRead').mockResolvedValue({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'nope' }
      });

      const { result } = renderHook(() => useNotificationStream('u1', factory));
      await flush();

      await act(async () => {
        await result.current.markRead('n1');
      });

      expect(result.current.notifications[0].readAt).toBeNull();
      expect(result.current.unreadCount).toBe(1);
    });
  });
});
