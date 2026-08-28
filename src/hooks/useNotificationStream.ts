import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getNotifications,
  getUnreadCount,
  issueStreamTicket,
  markNotificationRead,
  onForcedLogout,
  type NotificationRecord
} from '../webApiClient';

/**
 * 알림 SSE 스트림 훅 (Phase 15 - B-2).
 *
 * 재연결과 정리 로직이 이 기능의 위험이 몰린 곳이라, 표현 컴포넌트가 아니라
 * 여기에 전부 담아 테스트 가능한 .ts로 둔다.
 */

export type StreamStatus = 'idle' | 'connecting' | 'open' | 'retrying' | 'stopped';

/** 재연결 백오프. 티켓 한도(20회/분)에 닿지 않도록 1초에서 30초까지 지수적으로 늘린다. */
const BASE_RETRY_MS = 1_000;
const MAX_RETRY_MS = 30_000;

/**
 * EventSource와 같은 최소 인터페이스. happy-dom 테스트 환경에는 EventSource가
 * 아예 없어(전역·window 모두 undefined) 스파이도 폴리필도 쓸 수 없으므로,
 * 생성 자체를 주입받는다.
 */
export interface StreamLike {
  addEventListener(type: string, listener: (event: { data?: string }) => void): void;
  close(): void;
  onerror: ((event: unknown) => void) | null;
}

export type StreamFactory = (url: string) => StreamLike;

const defaultFactory: StreamFactory = (url) => new EventSource(url) as unknown as StreamLike;

export interface UseNotificationStreamResult {
  notifications: NotificationRecord[];
  unreadCount: number;
  status: StreamStatus;
  markRead: (id: string) => Promise<void>;
}

export function useNotificationStream(
  userId: string | null,
  createStream: StreamFactory = defaultFactory
): UseNotificationStreamResult {
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [status, setStatus] = useState<StreamStatus>('idle');

  // 재연결 시도 횟수는 리렌더를 유발할 필요가 없고, effect 안에서만 읽고 쓴다.
  const attemptRef = useRef(0);

  useEffect(() => {
    if (!userId) {
      setStatus('idle');
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    let cancelled = false;
    let stream: StreamLike | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const teardown = (): void => {
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
      stream?.close();
      stream = null;
    };

    /** 강제 로그아웃 시 스트림이 남아 있으면 로그아웃한 사용자에게 알림이 계속 흐른다. */
    const unsubscribeLogout = onForcedLogout(() => {
      cancelled = true;
      teardown();
      setStatus('stopped');
    });

    const scheduleRetry = (): void => {
      const delay = Math.min(BASE_RETRY_MS * 2 ** attemptRef.current, MAX_RETRY_MS);
      attemptRef.current += 1;
      setStatus('retrying');
      // 지터: 서버 재시작 후 모든 클라이언트가 같은 순간에 몰려 돌아오는 것을 막는다.
      timer = setTimeout(connect, delay + Math.random() * 250);
    };

    async function connect(): Promise<void> {
      if (cancelled) return;
      setStatus('connecting');

      const ticketResult = await issueStreamTicket();
      if (cancelled) return;

      if (!ticketResult.success) {
        // 발급 자체가 실패(429·네트워크 등)해도 같은 백오프로 물러난다.
        scheduleRetry();
        return;
      }

      const source = createStream(`/api/notifications/stream?ticket=${ticketResult.data.ticket}`);
      stream = source;

      source.addEventListener('connected', () => {
        if (cancelled) return;
        attemptRef.current = 0; // 성공했으므로 백오프를 초기화한다.
        setStatus('open');
      });

      source.addEventListener('notification', (event) => {
        if (cancelled || !event.data) return;
        try {
          const record = JSON.parse(event.data) as NotificationRecord;
          setNotifications((current) => [record, ...current]);
          if (!record.readAt) setUnreadCount((count) => count + 1);
        } catch {
          // 깨진 프레임 하나가 스트림 전체를 끊게 두지 않는다.
        }
      });

      // 서버가 세션 종료로 스트림을 끊은 경우다. 재연결하면 안 된다 — 티켓 발급이
      // 아직 통과하는 짧은 창 동안 다시 붙었다 끊기는 것을 반복하게 된다.
      source.addEventListener('revoked', () => {
        cancelled = true;
        teardown();
        setStatus('stopped');
      });

      // 서버가 스트림 최대 수명(액세스 토큰 TTL에 맞춘 값)에 도달해 재연결을
      // 요구하는 경우다. revoked와 달리 실패가 아니므로 즉시 새 티켓을 받아
      // 다시 연결한다 — 티켓 발급이 유효한 JWT를 요구하므로, 이 왕복 자체가
      // 세션이 아직 유효한지 다시 확인하는 역할을 한다. teardown()으로 스트림을
      // 동기적으로 닫아 곧이어 오는 onerror가 중복으로 재연결을 예약하지 않게 한다.
      source.addEventListener('reauth', () => {
        if (cancelled) return;
        teardown();
        attemptRef.current = 0; // 실패가 아니므로 백오프를 물리지 않는다.
        setStatus('connecting');
        // 지터: 배포 직후처럼 여러 스트림이 비슷한 시각에 열렸다면 수명도
        // 비슷하게 끝나므로, 재연결이 한꺼번에 몰리는 것을 흩어놓는다.
        timer = setTimeout(connect, Math.random() * 3000);
      });

      source.onerror = () => {
        // EventSource는 끊기면 같은 URL로 자동 재연결하는데, 그 URL의 티켓은 이미
        // 소진돼 401을 받고 또 끊긴다. close()로 브라우저의 재연결을 차단하고
        // 새 티켓으로 우리가 직접 다시 연다.
        source.close();

        // reauth 등으로 이미 새 연결로 넘어간 뒤에 옛 연결의 지연된 error가
        // 뒤따라 도착할 수 있다 — close()가 후속 이벤트를 막는다는 보장에만
        // 기대지 않고, 지금 활성 스트림이 이 source가 맞는지 직접 확인한다.
        // 아니라면 이미 처리가 끝난 연결의 뒤늦은 신호이므로 무시한다.
        if (stream !== source) return;
        stream = null;

        if (cancelled) return;
        scheduleRetry();
      };
    }

    // 스트림은 연결 이후 발생분만 주므로 초기 목록은 따로 채운다.
    void (async () => {
      const [listResult, countResult] = await Promise.all([
        getNotifications(userId, { limit: 50 }),
        getUnreadCount(userId)
      ]);
      if (cancelled) return;
      if (listResult.success) setNotifications(listResult.data);
      if (countResult.success) setUnreadCount(countResult.data.count);
    })();

    void connect();

    return () => {
      cancelled = true;
      unsubscribeLogout();
      teardown();
    };
  }, [userId, createStream]);

  const markRead = useCallback(
    async (id: string): Promise<void> => {
      if (!userId) return;

      const previous = notifications;
      const previousCount = unreadCount;

      // 낙관적 갱신 — 실패하면 되돌린다.
      setNotifications((current) =>
        current.map((n) => (n.id === id && !n.readAt ? { ...n, readAt: new Date().toISOString() } : n))
      );
      setUnreadCount((count) => Math.max(0, count - 1));

      const result = await markNotificationRead(userId, id);
      if (!result.success) {
        setNotifications(previous);
        setUnreadCount(previousCount);
      }
    },
    [userId, notifications, unreadCount]
  );

  return { notifications, unreadCount, status, markRead };
}
