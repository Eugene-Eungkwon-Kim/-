"""공용 HTTP 클라이언트 (requests 기반).

일시적 오류(타임아웃, 429, 5xx)는 지수 백오프로 자동 재시도하고,
인증/쿼터 오류와 응답 구조 오류는 구분해서 즉시 호출자에게 알린다.
fetch_realestate.py에서 검증한 오류 분류·종료코드 규약(CLAUDE.md 참고)을
requests 기반 수집기에도 동일하게 적용하기 위한 모듈이다.
"""

import logging
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_S = 2.0


class TransientFetchError(Exception):
    """재시도하면 해결될 수 있는 오류 (타임아웃, 429, 5xx, 연결 오류)."""


class AuthFetchError(Exception):
    """인증/쿼터 문제. 재시도로 해결되지 않으므로 호출자가 즉시 중단해야 한다."""


class SchemaFetchError(Exception):
    """응답 구조가 예상과 다른 경우 (JSON 파싱 실패, 예기치 않은 HTTP 오류 등)."""


def get_with_retry(
    session: requests.Session,
    url: str,
    *,
    params: Optional[dict] = None,
    timeout: float = 10,
    max_retries: int = MAX_RETRIES,
    retry_base_s: float = RETRY_BASE_S,
) -> requests.Response:
    """오류를 분류하며 재시도하는 GET 요청.

    HTTP 401/403은 AuthFetchError, 429·5xx는 재시도 후에도 실패하면
    TransientFetchError, 그 외 HTTP 오류·요청 실패는 SchemaFetchError로
    던진다. API가 HTTP 200으로 자체 오류를 표현하는 경우(예: VWorld의
    response.status, Opinet의 result 누락)는 API마다 스키마가 달라 이
    함수가 판단할 수 없으므로, 호출자가 응답 본문을 보고 직접 분류해야 한다.
    """
    attempt = 0
    while True:
        transient_reason = None
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (401, 403):
                raise AuthFetchError(f"인증 오류 (HTTP {status}): {e}") from e
            if status == 429 or (status is not None and 500 <= status < 600):
                transient_reason = f"HTTP {status}"
            else:
                raise SchemaFetchError(f"예기치 않은 HTTP 오류 ({status}): {e}") from e
        except requests.exceptions.Timeout as e:
            transient_reason = f"타임아웃: {e}"
        except requests.exceptions.ConnectionError as e:
            transient_reason = f"연결 오류: {e}"
        except requests.exceptions.RequestException as e:
            raise SchemaFetchError(f"요청 실패: {e}") from e

        attempt += 1
        if attempt > max_retries:
            raise TransientFetchError(f"{max_retries}회 재시도 후 실패 ({transient_reason}): {url}")
        wait = retry_base_s * (2 ** (attempt - 1))
        logger.info("일시적 오류, %.0f초 후 재시도 (%d/%d) — %s", wait, attempt, max_retries, transient_reason)
        time.sleep(wait)


def get_json_with_retry(session: requests.Session, url: str, **kwargs: Any) -> Any:
    """get_with_retry() 후 JSON으로 파싱. 파싱 실패는 SchemaFetchError로 던진다."""
    response = get_with_retry(session, url, **kwargs)
    try:
        return response.json()
    except ValueError as e:
        raise SchemaFetchError(f"JSON 파싱 실패(응답 구조 변경 가능성): {e}") from e
