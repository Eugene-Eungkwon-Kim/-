"""Tier 2 게이트웨이: 3개 보안 필터

필터:
  1. 인증 (Authentication)
  2. 속도제한 (Rate limiting)
  3. 요청검증 (Request validation)

실행:
    python -m pytest tests/test_tier2_gateway.py -v
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import time
import logging
import hashlib

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

app = FastAPI(title="Loan4U AVM Gateway", version="1.0.0")


# ============================================================
# 1. 인증 필터 (Authentication)
# ============================================================


class AuthenticationFilter:
    """API 키 기반 인증."""

    VALID_KEYS = {
        "test_key_001": "user_1",
        "test_key_002": "user_2",
        "test_key_003": "admin",
    }

    @classmethod
    def validate_key(cls, api_key: str) -> Optional[str]:
        """API 키 검증.

        Args:
            api_key: API 키

        Returns:
            사용자명 또는 None
        """
        return cls.VALID_KEYS.get(api_key)

    @classmethod
    def get_api_key(cls, request: Request) -> str:
        """요청에서 API 키 추출.

        Args:
            request: HTTP 요청

        Returns:
            API 키

        Raises:
            HTTPException: 키 없음
        """
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header")
        return api_key


async def verify_api_key(request: Request) -> str:
    """API 키 검증 의존성.

    Args:
        request: HTTP 요청

    Returns:
        사용자명

    Raises:
        HTTPException: 인증 실패
    """
    api_key = AuthenticationFilter.get_api_key(request)
    user = AuthenticationFilter.validate_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


# ============================================================
# 2. 속도제한 필터 (Rate limiting)
# ============================================================


class RateLimiter:
    """토큰 버킷 기반 속도제한."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """초기화.

        Args:
            max_requests: 시간 윈도우당 최대 요청
            window_seconds: 시간 윈도우 (초)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.buckets: Dict[str, list] = {}

    def is_allowed(self, client_id: str) -> bool:
        """요청 허용 여부 판정.

        Args:
            client_id: 클라이언트 ID

        Returns:
            허용 여부
        """
        now = time.time()

        # 클라이언트별 요청 타임스탬프 초기화
        if client_id not in self.buckets:
            self.buckets[client_id] = []

        # 윈도우 벗어난 요청 제거
        self.buckets[client_id] = [
            ts for ts in self.buckets[client_id]
            if now - ts < self.window_seconds
        ]

        # 제한 초과 여부 확인
        if len(self.buckets[client_id]) >= self.max_requests:
            return False

        # 요청 기록
        self.buckets[client_id].append(now)
        return True


rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


async def check_rate_limit(request: Request) -> None:
    """속도제한 검증 의존성.

    Args:
        request: HTTP 요청

    Raises:
        HTTPException: 제한 초과
    """
    client_id = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


# ============================================================
# 3. 요청검증 필터 (Request validation)
# ============================================================


class RequestValidator:
    """요청 유효성 검증."""

    @staticmethod
    def validate_address(address: str) -> bool:
        """주소 검증.

        Args:
            address: 주소

        Returns:
            유효 여부
        """
        if not address or len(address) < 3 or len(address) > 500:
            return False
        return True

    @staticmethod
    def validate_property_type(property_type: str) -> bool:
        """부동산 유형 검증.

        Args:
            property_type: 유형

        Returns:
            유효 여부
        """
        valid_types = ["apartment", "house", "land", "commercial"]
        return property_type in valid_types

    @staticmethod
    def validate_area(area_sqm: Optional[float]) -> bool:
        """면적 검증.

        Args:
            area_sqm: 면적 (제곱미터)

        Returns:
            유효 여부
        """
        if area_sqm is None:
            return True
        return 1 <= area_sqm <= 1000


async def validate_request(
    address: str,
    property_type: str,
    area_sqm: Optional[float] = None,
) -> None:
    """요청 유효성 검증 의존성.

    Args:
        address: 주소
        property_type: 부동산 유형
        area_sqm: 면적

    Raises:
        HTTPException: 검증 실패
    """
    if not RequestValidator.validate_address(address):
        raise HTTPException(status_code=400, detail="Invalid address")

    if not RequestValidator.validate_property_type(property_type):
        raise HTTPException(status_code=400, detail="Invalid property type")

    if not RequestValidator.validate_area(area_sqm):
        raise HTTPException(status_code=400, detail="Invalid area")


# ============================================================
# 보호된 엔드포인트
# ============================================================


@app.post("/protected/analyze")
async def protected_analyze(
    address: str,
    property_type: str,
    area_sqm: Optional[float] = None,
    user: str = Depends(verify_api_key),
    _: None = Depends(check_rate_limit),
    __: None = Depends(validate_request),
) -> Dict[str, Any]:
    """3개 필터를 통과한 보호된 분석 엔드포인트.

    Args:
        address: 주소
        property_type: 부동산 유형
        area_sqm: 면적 (선택)
        user: 인증된 사용자 (의존성)
        _: 속도제한 (의존성)
        __: 요청검증 (의존성)

    Returns:
        분석 결과
    """
    return {
        "status": "ok",
        "user": user,
        "address": address,
        "property_type": property_type,
        "area_sqm": area_sqm,
        "estimated_price": 500_000_000,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """게이트웨이 헬스체크.

    Returns:
        상태
    """
    return {"status": "healthy", "component": "gateway"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
