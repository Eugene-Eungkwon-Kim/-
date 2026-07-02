import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest';
import { getUserProfile, login, logout, onForcedLogout, setAuthToken, setRefreshTokenValue } from '../webApiClient';

function fakeResponse(status: number, body: unknown) {
  return { status, json: async () => body };
}

/** window.localStorage 스텁(vi.fn())에 실제 저장 동작을 부여한다 (test/setup.ts는 빈 vi.fn()만 제공) */
function mockLocalStorage(initial: Record<string, string> = {}) {
  const store: Record<string, string> = { ...initial };
  vi.mocked(localStorage.getItem).mockImplementation((key: string) => store[key] ?? null);
  vi.mocked(localStorage.setItem).mockImplementation((key: string, value: string) => {
    store[key] = value;
  });
  vi.mocked(localStorage.removeItem).mockImplementation((key: string) => {
    delete store[key];
  });
  return store;
}

describe('webApiClient (Day 9 - Task 4: 프론트엔드 토큰 영속화 & 자동 로그아웃, δ=1090)', () => {
  let fetchMock: Mock;

  beforeEach(() => {
    mockLocalStorage();
    // happy-dom 환경 초기화가 test/setup.ts의 global.fetch = vi.fn()을 실제 구현으로
    // 덮어쓰는 것을 확인했다 — vi.stubGlobal로 이 파일 안에서 확실하게 재정의한다.
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  it('저장된 accessToken이 있으면 모듈 로드 시 복원해 이후 요청에 사용한다', async () => {
    mockLocalStorage({ 'maars.accessToken': 'stored-access', 'maars.refreshToken': 'stored-refresh' });
    vi.resetModules();
    const freshModule = await import('../webApiClient');

    fetchMock.mockResolvedValue(fakeResponse(200, { success: true, data: {} }));
    await freshModule.getUserProfile('u1');

    const [, options] = fetchMock.mock.calls[0];
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer stored-access');
  });

  it('401을 받으면 refresh를 시도하고 성공하면 원 요청을 재시도한다', async () => {
    setAuthToken('expired-access');
    setRefreshTokenValue('valid-refresh');

    fetchMock
      .mockResolvedValueOnce(fakeResponse(401, { success: false, error: { code: 'UNAUTHORIZED' } })) // 원 요청
      .mockResolvedValueOnce(fakeResponse(200, { success: true, data: { token: 'new-access', refreshToken: 'new-refresh' } })) // refresh
      .mockResolvedValueOnce(fakeResponse(200, { success: true, data: { id: 'u1' } })); // 재시도

    const result = await getUserProfile('u1');

    expect(result).toEqual({ success: true, data: { id: 'u1' } });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/auth/refresh');
  });

  it('refresh도 실패하면 토큰을 지우고 forced-logout 구독자에게 알린다', async () => {
    setAuthToken('expired-access');
    setRefreshTokenValue('invalid-refresh');

    fetchMock
      .mockResolvedValueOnce(fakeResponse(401, { success: false, error: { code: 'UNAUTHORIZED' } }))
      .mockResolvedValueOnce(fakeResponse(401, { success: false, error: { code: 'INVALID_REFRESH_TOKEN' } }));

    const onLogout = vi.fn();
    const unsubscribe = onForcedLogout(onLogout);

    await getUserProfile('u1');

    expect(onLogout).toHaveBeenCalledTimes(1);
    expect(localStorage.removeItem).toHaveBeenCalledWith('maars.accessToken');
    unsubscribe();
  });

  it('logout()은 서버 호출이 실패해도 로컬 토큰을 지운다', async () => {
    setAuthToken('access-1');
    setRefreshTokenValue('refresh-1');
    fetchMock.mockRejectedValue(new Error('network down'));

    await logout();

    expect(localStorage.removeItem).toHaveBeenCalledWith('maars.accessToken');
    expect(localStorage.removeItem).toHaveBeenCalledWith('maars.refreshToken');
  });

  it('구독 해제 후에는 forced-logout 콜백이 호출되지 않는다', async () => {
    setAuthToken('expired-access');
    setRefreshTokenValue('invalid-refresh');
    fetchMock
      .mockResolvedValueOnce(fakeResponse(401, { success: false, error: {} }))
      .mockResolvedValueOnce(fakeResponse(401, { success: false, error: {} }));

    const onLogout = vi.fn();
    const unsubscribe = onForcedLogout(onLogout);
    unsubscribe();

    await getUserProfile('u1');

    expect(onLogout).not.toHaveBeenCalled();
  });

  it('login()은 정상 응답을 그대로 반환한다', async () => {
    fetchMock.mockResolvedValue(fakeResponse(200, { success: true, data: { token: 't', refreshToken: 'r', user: { id: 'u1' } } }));
    const result = await login('a@example.com', 'pw');
    expect(result.success).toBe(true);
  });
});
