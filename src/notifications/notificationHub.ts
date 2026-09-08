import Redis from 'ioredis';
import type { NotificationRecord } from '../types/notification';

/**
 * 알림 팬아웃 계층 (Phase 15 - Section 2, B-5).
 *
 * cacheFactory와 같은 패턴: REDIS_URL이 있으면 인스턴스 간 전달, 없으면 프로세스
 * 내 전달로 강등한다. 단일 인스턴스 배포와 테스트에서는 Redis 없이도 동작한다.
 */
export interface NotificationHub {
  publish(notification: NotificationRecord): Promise<void>;
  /** 구독 해제 함수를 돌려준다. 호출자는 연결 종료 시 반드시 호출해야 한다. */
  subscribe(userId: string, listener: (n: NotificationRecord) => void): () => void;
  /**
   * 이 인스턴스가 들고 있는 해당 사용자의 구독 수. SSE 연결 상한 판정에 쓴다.
   *
   * 인스턴스 로컬 값이다 — 다중 인스턴스 배포에서 사용자는 인스턴스 수만큼 곱한
   * 만큼 열 수 있다. 전역 상한은 Redis 카운터가 필요한데 연결이 비정상 종료될 때
   * 카운터가 새는 문제를 함께 풀어야 해서 별도 작업으로 둔다. 로컬 상한만으로도
   * 한 클라이언트의 재연결 루프가 인스턴스를 고갈시키는 주된 시나리오는 막힌다.
   */
  subscriberCount(userId: string): number;
  /**
   * 해당 사용자의 열린 스트림을 모두 끊으라고 알린다 (로그아웃 등).
   *
   * SSE 연결은 티켓 1회로 인증되고 그 뒤로는 토큰을 싣지 않아 재인증되지 않는다.
   * 클라이언트가 닫아주기를 기대할 수만은 없으므로 서버가 끊을 수단이 필요하다.
   * Redis 허브에서는 모든 인스턴스로 전파된다.
   */
  revoke(userId: string): Promise<void>;
  /** 취소 신호를 받을 핸들러 등록. 해제 함수를 돌려준다. */
  onRevoke(userId: string, handler: () => void): () => void;
  close(): Promise<void>;
}

/**
 * 채널 페이로드. 알림과 취소가 같은 채널을 쓰므로 태그로 구분한다 — 채널을 하나
 * 더 두면 구독 관리가 두 배가 되고 순서 보장도 잃는다.
 */
type HubMessage =
  | { type: 'notification'; notification: NotificationRecord }
  | { type: 'revoke'; userId: string };

export const NOTIFICATION_CHANNEL = 'maars:notifications';

/**
 * userId → 리스너 집합. 로컬 SSE 접속을 관리하는 공통 레지스트리로,
 * 메모리 허브와 Redis 허브가 모두 이 위에서 라우팅한다.
 */
class ListenerRegistry {
  private readonly listeners = new Map<string, Set<(n: NotificationRecord) => void>>();
  private readonly revokeHandlers = new Map<string, Set<() => void>>();

  add(userId: string, listener: (n: NotificationRecord) => void): () => void {
    let set = this.listeners.get(userId);
    if (!set) {
      set = new Set();
      this.listeners.set(userId, set);
    }
    set.add(listener);

    return () => {
      const current = this.listeners.get(userId);
      if (!current) return;
      current.delete(listener);
      // 빈 Set을 남겨두면 접속이 많았던 사용자만큼 Map이 계속 커진다.
      if (current.size === 0) this.listeners.delete(userId);
    };
  }

  count(userId: string): number {
    return this.listeners.get(userId)?.size ?? 0;
  }

  addRevokeHandler(userId: string, handler: () => void): () => void {
    let set = this.revokeHandlers.get(userId);
    if (!set) {
      set = new Set();
      this.revokeHandlers.set(userId, set);
    }
    set.add(handler);

    return () => {
      const current = this.revokeHandlers.get(userId);
      if (!current) return;
      current.delete(handler);
      if (current.size === 0) this.revokeHandlers.delete(userId);
    };
  }

  dispatchRevoke(userId: string): void {
    // 핸들러가 스트림을 닫으면서 자기 자신을 해제하므로, 순회 중 변형을 피해 복사한다.
    for (const handler of [...(this.revokeHandlers.get(userId) ?? [])]) {
      try {
        handler();
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('[notificationHub] revoke handler failed:', error);
      }
    }
  }

  dispatch(notification: NotificationRecord): void {
    const set = this.listeners.get(notification.userId);
    if (!set) return;
    for (const listener of set) {
      try {
        listener(notification);
      } catch (error) {
        // 한 구독자의 쓰기 실패(끊긴 소켓 등)가 다른 구독자 전달을 막아선 안 된다.
        // eslint-disable-next-line no-console
        console.error('[notificationHub] listener failed:', error);
      }
    }
  }

  clear(): void {
    this.listeners.clear();
    this.revokeHandlers.clear();
  }
}

/** 단일 프로세스 전용. 다중 인스턴스에서는 다른 인스턴스의 구독자에게 전달되지 않는다. */
export class MemoryNotificationHub implements NotificationHub {
  private readonly registry = new ListenerRegistry();

  async publish(notification: NotificationRecord): Promise<void> {
    this.registry.dispatch(notification);
  }

  subscribe(userId: string, listener: (n: NotificationRecord) => void): () => void {
    return this.registry.add(userId, listener);
  }

  subscriberCount(userId: string): number {
    return this.registry.count(userId);
  }

  async revoke(userId: string): Promise<void> {
    this.registry.dispatchRevoke(userId);
  }

  onRevoke(userId: string, handler: () => void): () => void {
    return this.registry.addRevokeHandler(userId, handler);
  }

  async close(): Promise<void> {
    this.registry.clear();
  }
}

/**
 * 사용자별 채널(notifications:user:{id}) 대신 단일 채널을 쓴다.
 *
 * 사용자별 채널은 SSE 접속마다 SUBSCRIBE/UNSUBSCRIBE를 관리해야 하고 구독 수가
 * 접속 수만큼 늘어난다. 대신 인스턴스당 구독 연결 1개로 모든 알림을 받아
 * 페이로드의 userId로 로컬 라우팅한다. 대가는 모든 인스턴스가 모든 알림을 받는
 * 것인데, 알림은 상태 전이에만 발생해 초당 수 건 규모라 무시할 수 있다.
 */
export class RedisNotificationHub implements NotificationHub {
  private readonly publisher: Redis;
  private readonly subscriber: Redis;
  private readonly registry = new ListenerRegistry();
  private ready: Promise<void>;

  constructor(redisUrl: string) {
    // 구독 모드의 연결에서는 일반 명령을 실행할 수 없으므로 연결을 분리한다.
    // redisCacheStore의 연결을 재사용해서는 안 되는 이유이기도 하다.
    this.publisher = new Redis(redisUrl, { maxRetriesPerRequest: 1 });
    this.subscriber = new Redis(redisUrl, { maxRetriesPerRequest: 1 });

    this.subscriber.on('message', (channel, payload) => {
      if (channel !== NOTIFICATION_CHANNEL) return;
      try {
        const message = JSON.parse(payload) as HubMessage;
        if (message.type === 'notification') {
          this.registry.dispatch(message.notification);
        } else if (message.type === 'revoke') {
          this.registry.dispatchRevoke(message.userId);
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('[notificationHub] malformed payload:', error);
      }
    });

    this.ready = this.subscriber.subscribe(NOTIFICATION_CHANNEL).then(() => undefined);
  }

  async publish(notification: NotificationRecord): Promise<void> {
    const message: HubMessage = { type: 'notification', notification };
    await this.publisher.publish(NOTIFICATION_CHANNEL, JSON.stringify(message));
  }

  subscribe(userId: string, listener: (n: NotificationRecord) => void): () => void {
    return this.registry.add(userId, listener);
  }

  subscriberCount(userId: string): number {
    return this.registry.count(userId);
  }

  /** 모든 인스턴스에 전파된다 — 발행 인스턴스가 아닌 곳의 스트림도 끊긴다. */
  async revoke(userId: string): Promise<void> {
    const message: HubMessage = { type: 'revoke', userId };
    await this.publisher.publish(NOTIFICATION_CHANNEL, JSON.stringify(message));
  }

  onRevoke(userId: string, handler: () => void): () => void {
    return this.registry.addRevokeHandler(userId, handler);
  }

  /** SUBSCRIBE 완료를 기다린다 — 구독 직후 발행하는 테스트의 경합을 막는다. */
  async whenReady(): Promise<void> {
    await this.ready;
  }

  async close(): Promise<void> {
    this.registry.clear();
    await Promise.allSettled([this.publisher.quit(), this.subscriber.quit()]);
  }
}

export function createNotificationHub(): NotificationHub {
  const redisUrl = process.env.REDIS_URL;
  return redisUrl ? new RedisNotificationHub(redisUrl) : new MemoryNotificationHub();
}
