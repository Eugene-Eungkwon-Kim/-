import type { NotificationRecord } from '../webApiClient';
import type { StreamStatus } from '../hooks/useNotificationStream';

/**
 * 알림 배지와 목록 (Phase 15 - B-2).
 *
 * 표현 전용이다 — 연결·재연결·정리 로직은 전부 useNotificationStream에 있다.
 * App.tsx와 같은 인라인 스타일 관례를 따르고 스타일 시스템을 새로 들이지 않는다.
 */

const SEVERITY_COLOR: Record<NotificationRecord['severity'], string> = {
  critical: '#c2371f',
  warning: '#b4690e',
  resolved: '#1b7f5a'
};

const SEVERITY_LABEL: Record<NotificationRecord['severity'], string> = {
  critical: '위험',
  warning: '경고',
  resolved: '해소'
};

const STATUS_HINT: Record<StreamStatus, string> = {
  idle: '',
  connecting: '연결 중…',
  open: '실시간 연결됨',
  retrying: '재연결 중…',
  stopped: '연결 종료됨'
};

export interface NotificationBellProps {
  notifications: NotificationRecord[];
  unreadCount: number;
  status: StreamStatus;
  onMarkRead: (id: string) => void;
}

export default function NotificationBell({ notifications, unreadCount, status, onMarkRead }: NotificationBellProps) {
  return (
    <section style={{ border: '1px solid #ddd', borderRadius: 8, padding: 16, marginTop: 24 }}>
      <header style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12 }}>
        <h2 style={{ margin: 0, fontSize: '1.1rem' }}>
          알림
          {unreadCount > 0 && (
            <span
              aria-label={`읽지 않은 알림 ${unreadCount}건`}
              style={{
                marginLeft: 8,
                background: '#c2371f',
                color: '#fff',
                borderRadius: 999,
                padding: '1px 8px',
                fontSize: '0.75rem'
              }}
            >
              {unreadCount}
            </span>
          )}
        </h2>
        <span style={{ fontSize: '0.75rem', color: '#666' }}>{STATUS_HINT[status]}</span>
      </header>

      {notifications.length === 0 ? (
        <p style={{ color: '#666', fontSize: '0.875rem', margin: 0 }}>알림이 없습니다.</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {notifications.map((n) => (
            <li
              key={n.id}
              style={{
                borderLeft: `3px solid ${SEVERITY_COLOR[n.severity]}`,
                padding: '8px 12px',
                marginBottom: 6,
                background: n.readAt ? 'transparent' : '#f6f8fb',
                display: 'flex',
                justifyContent: 'space-between',
                gap: 12
              }}
            >
              <span style={{ fontSize: '0.875rem' }}>
                <strong style={{ color: SEVERITY_COLOR[n.severity] }}>{SEVERITY_LABEL[n.severity]}</strong>
                {` · ${n.metric} = ${n.value} (기준 ${n.threshold}) · ${n.snapshotDate}`}
              </span>
              {!n.readAt && (
                <button type="button" onClick={() => onMarkRead(n.id)} style={{ fontSize: '0.75rem' }}>
                  읽음
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
