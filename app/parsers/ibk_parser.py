"""
IBK Data Disk 파서
시트 구조: Sheet A(차주), Sheet B(채권), Sheet C-1(담보물건), Sheet C-2(등기), Sheet C-3(설정순위), Sheet D(신용보증)
헤더 row 10(엑셀 1-based)의 키워드로 컬럼 위치를 자동 감지한다.
"""
import re
from datetime import date
from pathlib import Path
import openpyxl

from app.parsers.base_parser import BaseParser, DealRecord, DebtorRecord, PropertyRecord


# Sheet C-1: 고정 위치 컬럼 (헤더 행에 관계없이 항상 같은 위치, col_idx → field_name)
C1_FIXED = {
    1:  "serial_no",
    2:  "pool_class",
    3:  "debtor_type",
    4:  "debtor_serial",
    5:  "debtor_name",
    6:  "property_serial",
    7:  "property_index",
    8:  "address_sido",
    9:  "address_sigungu",
    10: "address_dong",
    11: "address_detail",
    12: "property_type",
    13: "land_area",
    14: "building_area",
    15: "other_area",
    16: "factory_mortgage",
    17: "ibk_first_set_date",
    18: "mortgage_rank",
    19: "currency",
    20: "mortgage_amount",
    21: "mortgage_amount_krw",
}

# 헤더 키워드 → 필드명 매핑 (부분 문자열 매칭)
C1_HEADER_KEYWORDS = {
    "근저당권설정액": "mortgage_amount_krw",
    "환산된 Property별\n근저당권설정액": "mortgage_amount_krw",
    "Property별\n선순위 설정순위": "senior_rank",
    "환산후 Property별\n선순위근저당권": "senior_mortgage_krw",
    "선순위\n가압류": "has_provisional_seizure",
    "가압류/압류/가처분 금액": "provisional_seizure_amount",
    "유치권 유무": "has_lien",
    "유치권 신고금액": "lien_amount",
    "소액보증금 (주택)": "small_deposit_housing",
    "소액보증금 (상가)": "small_deposit_commercial",
    "임차보증금 (주택)": "lease_deposit_housing",
    "임차보증금 (상가)": "lease_deposit_commercial",
    "선순위 임금채권": "wage_claim",
    "선순위 당해세": "current_tax",
    "선순위 조세채권": "tax_claim",
    "합계": "senior_burden_total",
    "감정평가구분": "appraisal_type",
    "감정평가일자": "appraisal_date",
    "감정평가기관": "appraiser",
    "토지감정평가액": "land_value",
    "건물 감정평가액": "building_value",
    "기계평가액": "machine_value",
    "제시외": "outside_value",
    "감정평가액합계": "total_value",
    "KB아파트시세": "kb_market_price",
    "경매개시": "is_filed",
    "경매 관할법원": "court",
    "경매신청기관\n(IBK)": "ibk_creditor",
    "경매개시일자\n(IBK)": "ibk_filing_date",
    "경매사건번호\n(IBK)": "ibk_case_number",
    "배당요구종기일\n(IBK)": "ibk_demand_deadline",
    "청구금액\n(IBK)": "ibk_claim_amount",
    "최초법사가": "first_legal_price",
    "최초경매기일": "first_auction_date",
    "최종경매회차": "lapse_count_raw",
    "최종경매결과": "final_result",
    "최종경매기일": "final_auction_date",
    "차기경매기일": "next_auction_date",
    "낙찰금액": "hammer_price",
    "최종경매일의": "final_min_bid",
    "차후예정경매일의": "next_min_bid",
}


class IBKParser(BaseParser):

    def parse(self, file_path: str) -> DealRecord:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        deal = self._parse_deal_meta(wb, file_path)

        if "Sheet C-1" in wb.sheetnames:
            self._parse_c1(wb["Sheet C-1"], deal)

        wb.close()
        return deal

    def _parse_deal_meta(self, wb, file_path: str) -> DealRecord:
        deal = DealRecord(source_file=file_path, financial_institution="IBK")

        # Sheet B에서 딜명/풀명/자산확정일 추출
        if "Sheet B" in wb.sheetnames:
            ws = wb["Sheet B"]
            rows = list(ws.iter_rows(min_row=1, max_row=6, values_only=True))
            for row in rows:
                for i, cell in enumerate(row):
                    if cell and "Program" in str(cell):
                        deal.deal_name = str(cell).strip()
                    if cell and "Pool" in str(cell) and i == 0:
                        deal.pool_name = str(cell).strip()
                    if cell and "자산확정일" in str(cell):
                        val = row[i + 1] if i + 1 < len(row) else None
                        deal.asset_date = self._clean_date(val)

        # 파일명에서 딜명 보완
        stem = Path(file_path).stem
        if not deal.deal_name:
            m = re.search(r"IBK[\s_]*(\d{4}-\d+)", stem, re.IGNORECASE)
            if m:
                deal.deal_name = f"IBK {m.group(1)} Program"

        return deal

    def _build_col_map(self, ws) -> dict[str, int]:
        """헤더 행(row 7~12)을 스캔해서 필드명 → 컬럼 인덱스(0-based) 매핑 구성"""
        col_map = dict(C1_FIXED)  # 고정 컬럼 먼저
        reverse = {}  # field_name → col_idx

        for row in ws.iter_rows(min_row=7, max_row=12, values_only=True):
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                for keyword, field in C1_HEADER_KEYWORDS.items():
                    if keyword in cell_str and field not in reverse:
                        reverse[field] = idx
            if len(reverse) >= 20:
                break

        col_map.update({v: k for k, v in reverse.items()})
        return reverse  # field_name → col_idx

    def _parse_c1(self, ws, deal: DealRecord):
        debtors: dict[str, DebtorRecord] = {}
        col_map = self._build_col_map(ws)  # field_name → col_idx

        # 고정 컬럼 추가 (fixed map은 col_idx → field_name이므로 반전)
        fixed_by_name = {v: k for k, v in C1_FIXED.items()}
        col_map.update(fixed_by_name)

        data_start = self._find_data_start(ws)

        for row in ws.iter_rows(min_row=data_start, values_only=True):
            # 빈 행 스킵
            if not any(row):
                continue
            if len(row) < 2 or row[1] is None:
                continue

            r = {field: (row[idx] if idx < len(row) else None)
                 for field, idx in col_map.items()}
            # 누락 키 기본값 보장
            for k in ("currency", "debtor_serial", "debtor_name", "debtor_type", "pool_class"):
                r.setdefault(k, None)

            debtor_serial = str(r["debtor_serial"] or "").strip()
            if not debtor_serial:
                continue

            if debtor_serial not in debtors:
                d = DebtorRecord(
                    debtor_serial=debtor_serial,
                    debtor_name=str(r["debtor_name"] or "").strip(),
                    debtor_type=str(r["debtor_type"] or "Regular").strip(),
                    pool_class=str(r["pool_class"] or "A").strip(),
                )
                debtors[debtor_serial] = d

            prop = PropertyRecord(
                property_serial=str(r["property_serial"] or "").strip(),
                property_index=self._safe_int(r["property_index"]),
                address_sido=str(r["address_sido"] or "").strip(),
                address_sigungu=str(r["address_sigungu"] or "").strip(),
                address_dong=str(r["address_dong"] or "").strip(),
                address_detail=str(r["address_detail"] or "").strip(),
                property_type=str(r["property_type"] or "").strip(),
                land_area=self._clean_float(r["land_area"]),
                building_area=self._clean_float(r["building_area"]),
                currency=str(r["currency"] or "KRW").strip(),
                mortgage_amount=self._clean_amount(r["mortgage_amount_krw"]),
                mortgage_rank=str(r["mortgage_rank"] or "").strip(),
                senior_mortgage_amount=self._clean_amount(r["senior_mortgage_krw"]),
                has_provisional_seizure=self._parse_yn(r["has_provisional_seizure"]),
                provisional_seizure_amount=self._clean_amount(r["provisional_seizure_amount"]),
                has_lien=self._parse_yn(r["has_lien"]),
                lien_amount=self._clean_amount(r["lien_amount"]),
                small_deposit_housing=self._clean_amount(r["small_deposit_housing"]),
                small_deposit_commercial=self._clean_amount(r["small_deposit_commercial"]),
                lease_deposit_housing=self._clean_amount(r["lease_deposit_housing"]),
                lease_deposit_commercial=self._clean_amount(r["lease_deposit_commercial"]),
                wage_claim=self._clean_amount(r["wage_claim"]),
                current_tax=self._clean_amount(r["current_tax"]),
                tax_claim=self._clean_amount(r["tax_claim"]),
                senior_burden_total=self._clean_amount(r["senior_burden_total"]),
                kb_market_price=self._clean_amount(r["kb_market_price"]),
                appraisal_type=str(r["appraisal_type"] or "").strip(),
                appraisal_date=self._clean_date(r["appraisal_date"]),
                appraiser=str(r["appraiser"] or "").strip(),
                land_value=self._clean_amount(r["land_value"]),
                building_value=self._clean_amount(r["building_value"]),
                machine_value=self._clean_amount(r["machine_value"]),
                outside_value=self._clean_amount(r["outside_value"]),
                total_value=self._clean_amount(r["total_value"]),
                is_filed=self._parse_filed(r["is_filed"]),
                court=str(r["court"] or "").strip(),
                creditor=str(r["ibk_creditor"] or "").strip(),
                case_number=str(r["ibk_case_number"] or "").strip(),
                filing_date=self._clean_date(r["ibk_filing_date"]),
                demand_deadline=self._clean_date(r["ibk_demand_deadline"]),
                claim_amount=self._clean_amount(r["ibk_claim_amount"]),
                first_legal_price=self._clean_amount(r["first_legal_price"]),
                first_auction_date=self._clean_date(r["first_auction_date"]),
                lapse_count=self._parse_lapse(r["lapse_count_raw"]),
                final_result=str(r["final_result"] or "").strip(),
                final_auction_date=self._clean_date(r["final_auction_date"]),
                next_auction_date=self._clean_date(r["next_auction_date"]),
                hammer_price=self._clean_amount(r["hammer_price"]),
                final_min_bid=self._clean_amount(r["final_min_bid"]),
                next_min_bid=self._clean_amount(r["next_min_bid"]),
            )
            prop.property_category = self._infer_category(prop.property_type)
            prop.address_full = " ".join(filter(None, [
                prop.address_sido, prop.address_sigungu,
                prop.address_dong, prop.address_detail
            ]))

            debtors[debtor_serial].properties.append(prop)

        deal.debtors = list(debtors.values())

    def _find_data_start(self, ws) -> int:
        """두 번째 셀이 숫자(일련번호)인 첫 행 탐색 → 데이터 시작 행(1-based)"""
        for row_idx, r_obj in enumerate(ws.iter_rows(min_row=8, max_row=20), start=8):
            if len(r_obj) > 1 and r_obj[1].value is not None:
                try:
                    int(float(str(r_obj[1].value).replace(",", "")))
                    return row_idx
                except (ValueError, TypeError):
                    pass
        return 11  # fallback

    def _parse_yn(self, value) -> bool | None:
        if value is None:
            return None
        s = str(value).strip()
        if s in ("Y", "유", "있음", "1"):
            return True
        if s in ("N", "무", "없음", "0"):
            return False
        return None

    def _parse_filed(self, value) -> bool | None:
        if value is None:
            return None
        s = str(value).strip()
        if s in ("Filed", "Y", "개시"):
            return True
        if s in ("Not Filed", "N", "미개시"):
            return False
        return None

    def _parse_lapse(self, value) -> int | None:
        # "최종경매회차" 컬럼에서 유찰회수 추정 (회차 - 1)
        n = self._safe_int(value)
        if n is None:
            return None
        return max(0, n - 1)

    def _safe_int(self, value) -> int | None:
        if value is None:
            return None
        try:
            return int(float(str(value).replace(",", "")))
        except Exception:
            return None
