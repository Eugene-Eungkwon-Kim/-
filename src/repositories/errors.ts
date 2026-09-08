export class DuplicateEmailError extends Error {
  constructor(email: string) {
    super(`Email already registered: ${email}`);
    this.name = 'DuplicateEmailError';
  }
}

export class UserNotFoundError extends Error {
  constructor(userId: string) {
    super(`User not found: ${userId}`);
    this.name = 'UserNotFoundError';
  }
}

export class OptimisticLockError extends Error {
  constructor(userId: string, expectedVersion: number, actualVersion: number) {
    super(
      `Version conflict for user ${userId}: expected ${expectedVersion}, but current version is ${actualVersion}`
    );
    this.name = 'OptimisticLockError';
  }
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class InvalidCredentialsError extends Error {
  constructor() {
    super('Invalid email or password');
    this.name = 'InvalidCredentialsError';
  }
}

export class InvalidRefreshTokenError extends Error {
  constructor() {
    super('Invalid or expired refresh token');
    this.name = 'InvalidRefreshTokenError';
  }
}

/**
 * 비교/조회 대상 스냅샷이 없을 때. 일반 Error로 던지면 errorMapping이
 * INTERNAL_ERROR(500)로 접어버려, 클라이언트가 잘못 지정한 날짜가 서버 장애처럼
 * 보고된다. 전용 타입으로 404에 매핑한다.
 */
export class SnapshotNotFoundError extends Error {
  constructor(userId: string, snapshotDate: string) {
    super(`Snapshot not found: user=${userId} date=${snapshotDate}`);
    this.name = 'SnapshotNotFoundError';
  }
}

/** 알림 단건 조회/읽음 처리 대상이 없을 때 (Phase 15 - Section 2) */
export class NotificationNotFoundError extends Error {
  constructor(notificationId: string) {
    super(`Notification not found: ${notificationId}`);
    this.name = 'NotificationNotFoundError';
  }
}
