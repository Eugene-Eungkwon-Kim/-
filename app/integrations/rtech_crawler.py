"""
rtech.or.kr 단지 마스터 크롤러

rtech(한국부동산원 공동주택관리정보시스템)에서
단지코드, 단지명, 주소 등 마스터 데이터를 수집합니다.

주의:
  - 웹 크롤링은 rtech 이용약관 검토 후 사용
  - 서버 부하를 줄이기 위해 요청 간 sleep 적용 (1초)
  - API 방식이 제공될 경우 우선 사용 권장
  - 현재 구현은 공공데이터(apts.go.kr) 활용 방식도 병행

사용방법:
    crawler = RtechCrawler()
    masters = crawler.fetch_complex_masters(sido="서울특별시")
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ComplexMaster:
    """단지 마스터 레코드"""
    complex_name: str
    address_sido: str
    address_sigungu: str
    address_dong: str = ""
    address_jibun: str = ""
    address_roadname: str = ""
    build_year: Optional[int] = None
    total_units: Optional[int] = None
    property_type: str = "아파트"
    complex_code: str = ""          # rtech 단지코드 (수집 가능 시)
    source: str = "rtech"

    def __post_init__(self):
        # complex_code가 없으면 이름+주소 기반 자동 생성
        if not self.complex_code:
            raw = f"{self.address_sido}{self.address_sigungu}{self.complex_name}"
            self.complex_code = "AUTO-" + hashlib.md5(raw.encode()).hexdigest()[:12]

    @property
    def address_full(self) -> str:
        parts = [self.address_sido, self.address_sigungu, self.address_dong,
                 self.address_jibun]
        return " ".join(p for p in parts if p)


class RtechCrawler:
    """
    rtech 단지 마스터 크롤러

    전략:
    1. 시도 목록 → 시군구 목록 → 단지 목록 순서로 탐색
    2. Rate limit: 요청당 1초 sleep (서버 부하 방지)
    3. 오류 발생 시 3회 재시도 후 skip
    """

    BASE_URL = "https://www.rtech.or.kr/portal"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    SIDO_LIST = [
        "서울특별시", "부산광역시", "대구광역시", "인천광역시",
        "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
        "경기도", "강원특별자치도", "충청북도", "충청남도",
        "전북특별자치도", "전라남도", "경상북도", "경상남도",
        "제주특별자치도",
    ]

    def __init__(self, sleep_sec: float = 1.0, retry: int = 3, timeout: int = 20):
        self.sleep_sec = sleep_sec
        self.retry = retry
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ─── 공개 메서드 ──────────────────────────────────────────

    def fetch_complex_masters(self, sido: Optional[str] = None,
                              max_pages: int = 9999) -> list[ComplexMaster]:
        """
        단지 마스터 수집

        Args:
            sido: 특정 시도만 수집 (None=전국)
            max_pages: 페이지 수 제한 (테스트용)

        Returns:
            ComplexMaster 리스트
        """
        targets = [sido] if sido else self.SIDO_LIST
        all_complexes: list[ComplexMaster] = []

        for sido_name in targets:
            logger.info(f"[rtech] {sido_name} 단지 수집 시작")
            try:
                complexes = self._fetch_sido(sido_name, max_pages)
                all_complexes.extend(complexes)
                logger.info(f"[rtech] {sido_name}: {len(complexes)}개 단지 수집")
            except Exception as e:
                logger.error(f"[rtech] {sido_name} 수집 오류: {e}")
                continue

        logger.info(f"[rtech] 전체 수집 완료: {len(all_complexes)}개 단지")
        return all_complexes

    # ─── 내부 메서드 ──────────────────────────────────────────

    def _fetch_sido(self, sido: str, max_pages: int) -> list[ComplexMaster]:
        """시도별 단지 목록 수집"""
        complexes = []
        page = 1

        while page <= max_pages:
            records = self._fetch_page(sido, page)
            if not records:
                break

            complexes.extend(records)
            page += 1
            time.sleep(self.sleep_sec)

        return complexes

    def _fetch_page(self, sido: str, page: int) -> list[ComplexMaster]:
        """단일 페이지 수집"""

        # rtech 검색 URL (실제 URL은 사이트 분석 후 수정 필요)
        url = f"{self.BASE_URL}/main/search/complexSearch.do"
        params = {
            "sido": sido,
            "pageNo": page,
            "pageSize": 20,
            "complexType": "01",    # 01=아파트, 02=다세대, 03=연립, 04=오피스텔
        }

        for attempt in range(self.retry):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()

                records = self._parse_complex_list(resp.text, sido)
                return records

            except requests.RequestException as e:
                logger.warning(f"[rtech] 페이지 {page} 조회 실패 (시도 {attempt+1}): {e}")
                time.sleep(2 * (attempt + 1))

        return []

    def _parse_complex_list(self, html: str, sido: str) -> list[ComplexMaster]:
        """HTML 파싱 → ComplexMaster 리스트"""

        soup = BeautifulSoup(html, "lxml")
        records = []

        # 실제 HTML 구조에 맞게 셀렉터 수정 필요
        # 아래는 일반적인 테이블 구조 기준 예시
        rows = soup.select("table.list-table tbody tr")

        if not rows:
            # tbody가 없는 경우
            rows = soup.select(".complex-list .complex-item")

        for row in rows:
            try:
                rec = self._parse_row(row, sido)
                if rec:
                    records.append(rec)
            except Exception as e:
                logger.debug(f"row 파싱 오류: {e}")
                continue

        return records

    def _parse_row(self, row, sido: str) -> Optional[ComplexMaster]:
        """단일 행 파싱"""

        # 셀 텍스트 추출 헬퍼
        def cell(selector: str, default: str = "") -> str:
            el = row.select_one(selector)
            return el.get_text(strip=True) if el else default

        # 단지명 (필수)
        complex_name = (
            cell("td.complex-name") or
            cell("td:nth-child(2)") or
            cell(".name")
        )
        if not complex_name:
            return None

        # 주소
        address_full = (
            cell("td.address") or
            cell("td:nth-child(3)") or
            cell(".address")
        )

        # 주소 파싱
        sido_val, sigungu_val, dong_val = self._parse_address(address_full, sido)

        # 건축년도
        year_str = cell("td.build-year") or cell("td:nth-child(4)")
        build_year = self._parse_year(year_str)

        # 총 호수
        units_str = cell("td.total-units") or cell("td:nth-child(5)")
        total_units = self._parse_int(units_str)

        # 단지코드 (data-id 속성 등에서 추출)
        complex_code = ""
        link = row.select_one("a[href]")
        if link:
            href = link.get("href", "")
            # complexNo=12345 형태에서 추출
            m = re.search(r"complexNo=(\w+)", href)
            if m:
                complex_code = m.group(1)

        return ComplexMaster(
            complex_name=complex_name,
            address_sido=sido_val,
            address_sigungu=sigungu_val,
            address_dong=dong_val,
            build_year=build_year,
            total_units=total_units,
            complex_code=complex_code,
            source="rtech",
        )

    @staticmethod
    def _parse_address(address: str, sido: str) -> tuple[str, str, str]:
        """
        주소 문자열 → (시도, 시군구, 동)

        예: "경기도 화성시 봉담읍 주석리"
            → ("경기도", "화성시", "봉담읍")
        """
        parts = address.strip().split()
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            return parts[0], parts[1], ""
        elif len(parts) == 1:
            return sido, parts[0], ""
        else:
            return sido, "", ""

    @staticmethod
    def _parse_year(val: str) -> Optional[int]:
        """연도 문자열 파싱"""
        m = re.search(r"(\d{4})", val)
        if m:
            year = int(m.group(1))
            if 1950 <= year <= 2030:
                return year
        return None

    @staticmethod
    def _parse_int(val: str) -> Optional[int]:
        """정수 파싱 (콤마 포함 가능)"""
        cleaned = re.sub(r"[^\d]", "", val)
        try:
            return int(cleaned) if cleaned else None
        except ValueError:
            return None


class AptGoKrCrawler:
    """
    공동주택관리정보시스템 (K-apt) 크롤러 — 대안 데이터 소스

    URL: https://www.k-apt.go.kr/
    제공: 공동주택 단지 정보, 관리비 공개
    특징: 국토부 운영으로 크롤링 부담이 rtech보다 낮음
    """

    BASE_URL = "https://www.k-apt.go.kr/kaptinfo"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    def __init__(self, sleep_sec: float = 1.0, timeout: int = 20):
        self.sleep_sec = sleep_sec
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch_complex_list(self, sgg_code: str) -> list[ComplexMaster]:
        """
        시군구 단위 공동주택 목록 조회

        K-apt는 단지코드(k_apt_code)를 제공
        이 코드를 complex_code로 활용
        """
        url = f"{self.BASE_URL}/kaptMgmtSttus/getKaptMgmtSttus.do"
        params = {
            "sggCd": sgg_code,
            "pageNo": 1,
            "pageSize": 1000,
        }

        complexes = []

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            rows = soup.select("tbody tr")

            for row in rows:
                cells = row.select("td")
                if len(cells) < 4:
                    continue

                complex_name = cells[1].get_text(strip=True)
                address = cells[2].get_text(strip=True)
                kapt_code = cells[0].get_text(strip=True)

                sido, sigungu, dong = RtechCrawler._parse_address(address, "")

                if complex_name:
                    complexes.append(ComplexMaster(
                        complex_name=complex_name,
                        address_sido=sido,
                        address_sigungu=sigungu,
                        address_dong=dong,
                        complex_code=f"KAPT-{kapt_code}" if kapt_code else "",
                        source="k-apt",
                    ))

            time.sleep(self.sleep_sec)

        except Exception as e:
            logger.error(f"K-apt {sgg_code} 조회 오류: {e}")

        return complexes
