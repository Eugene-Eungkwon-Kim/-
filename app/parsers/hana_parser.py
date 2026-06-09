"""
HANA Data Disk 파서
파일: HANA 거래사례/hana-A-*.xlsx (모든 파일이 동일한 전체 딜 데이터를 포함)
시트: "Allocation (2)"
헤더: Row 8(영어) + Row 9(한글) → Row 9 우선 사용
특이사항:
  - property_serial이 차주별 순번 → debtor_serial + "-" + 순번 조합
  - 감정평가 개별 항목(토지/건물...)은 "감정평가액 합계" 위치 기준 -4~-1 offset
  - 낙찰금액(C71), 최종경매결과(C63) 컬럼 포함
"""
import re
from pathlib import Path
import openpyxl

from app.parsers.ibk_parser import IBKParser, C1_HEADER_KEYWORDS
from app.parsers.base_parser import DealRecord, DebtorRecord, PropertyRecord

HANA_KEYWORDS = {
    "일련번호": "serial_no",
    "Pool 구분": "pool_class",
    "자산유형": "debtor_type",
    "차주관리번호": "debtor_serial",
    "차주명": "debtor_name",
    "Property 일련번호": "property_serial",
    "Property Address 1": "address_sido",
    "Property Address 2": "address_sigungu",
    "Property Address 3": "address_dong",
    "Property Address 4": "address_detail",
    "담보물형태": "property_type",
    "Property-대지면적": "land_area",
    "Property-건물면적": "building_area",
    "환산후 Property별 설정액": "mortgage_amount_krw",
    "법정 선순위 합계": "senior_burden_total",
    "경매개시\n여부": "is_filed",
    "경매청구금액\n(하나은행)": "claim_amount",
    "경매관할법원": "court",
    "사건번호 Ⅰ": "case_number",
    "경매개시일자\n(선행사건)": "filing_date",
    "배당요구종기일\n(선행사건)": "demand_deadline",
    "최초법사가": "first_legal_price",
    "최종경매회차": "lapse_count_raw",
    "최종경매결과": "final_result",
    "최초경매기일": "first_auction_date",
    "최종경매기일": "final_auction_date",
    "최종경매일의\n최저입찰금액": "final_min_bid",
    "차기경매기일": "next_auction_date",
    "차기경매일의\n최저입찰금액": "next_min_bid",
    "낙찰금액": "hammer_price",
    "감정평가 구분": "appraisal_type",
    "감정평가일자": "appraisal_date",
    "감정평가기관": "appraiser",
    "감정평가액 합계": "total_value",
    "KB아파트시세": "kb_market_price",
}


class HANAParser(IBKParser):

    def parse(self, file_path: str) -> DealRecord:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        deal = self._parse_deal_meta(wb, file_path)
        for sn in wb.sheetnames:
            if "Allocation" in sn and "(2)" in sn:
                self._parse_alloc_sheet(wb[sn], deal)
                break
        wb.close()
        return deal

    def _parse_deal_meta(self, wb, file_path: str) -> DealRecord:
        deal = DealRecord(source_file=file_path, financial_institution="HANA")
        # 시트에서 딜명 추출
        for sn in wb.sheetnames:
            if "Allocation" in sn and "(2)" in sn:
                ws = wb[sn]
                rows = list(ws.iter_rows(min_row=1, max_row=5, values_only=True))
                for row in rows:
                    for cell in row:
                        if cell and "HANA" in str(cell) and "Program" in str(cell):
                            deal.deal_name = str(cell).strip()
                            break
                break
        if not deal.deal_name:
            stem = Path(file_path).stem
            m = re.search(r"HANA[\s_]*(\d{4}-\d+[\w.]*)", stem, re.IGNORECASE)
            deal.deal_name = f"HANA {m.group(1)} Program" if m else stem[:60]
        deal.pool_name = "Pool A"
        return deal

    def _build_col_map(self, ws) -> dict[str, int]:
        """Row 7-9 스캔, HANA_KEYWORDS + C1_HEADER_KEYWORDS 매핑"""
        col_map: dict[str, int] = {}
        all_kw = {**HANA_KEYWORDS, **C1_HEADER_KEYWORDS}

        for row in ws.iter_rows(min_row=6, max_row=10, values_only=True):
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                for kw, field in all_kw.items():
                    if kw in cell_str and field not in col_map:
                        col_map[field] = idx

        # 감정평가 개별 항목: "감정평가액 합계" 기준 offset
        if "total_value" in col_map:
            tc = col_map["total_value"]
            col_map.setdefault("outside_value", tc - 1)
            col_map.setdefault("machine_value", tc - 2)
            col_map.setdefault("building_value", tc - 3)
            col_map.setdefault("land_value", tc - 4)

        return col_map

    def _find_data_start(self, ws) -> int:
        """HANA Row 7-8 Field/영어 헤더, Row 9 한글, Row 10+ 데이터"""
        for row_idx, r_obj in enumerate(ws.iter_rows(min_row=10, max_row=20), start=10):
            if len(r_obj) > 1 and r_obj[1].value is not None:
                try:
                    int(float(str(r_obj[1].value).replace(",", "")))
                    return row_idx
                except (ValueError, TypeError):
                    pass
        return 10

    def _parse_alloc_sheet(self, ws, deal: DealRecord):
        """Allocation (2) 시트 파싱"""
        debtors: dict[str, DebtorRecord] = {}
        col_map = self._build_col_map(ws)
        data_start = self._find_data_start(ws)

        for row in ws.iter_rows(min_row=data_start, values_only=True):
            if not any(row):
                continue
            if len(row) < 2 or row[1] is None:
                continue

            r = {field: (row[idx] if idx < len(row) else None)
                 for field, idx in col_map.items()}
            for k in ("currency", "debtor_serial", "debtor_name", "debtor_type", "pool_class"):
                r.setdefault(k, None)

            debtor_serial = str(r["debtor_serial"] or "").strip()
            if not debtor_serial:
                continue

            if debtor_serial not in debtors:
                debtors[debtor_serial] = DebtorRecord(
                    debtor_serial=debtor_serial,
                    debtor_name=str(r["debtor_name"] or "").strip(),
                    debtor_type=str(r["debtor_type"] or "Regular").strip(),
                    pool_class=str(r["pool_class"] or "A").strip(),
                )

            raw_serial = str(r.get("property_serial") or "").strip()
            prop_serial = f"{debtor_serial}-{raw_serial}" if raw_serial else debtor_serial

            prop = PropertyRecord(
                property_serial=prop_serial,
                address_sido=str(r.get("address_sido") or "").strip(),
                address_sigungu=str(r.get("address_sigungu") or "").strip(),
                address_dong=str(r.get("address_dong") or "").strip(),
                address_detail=str(r.get("address_detail") or "").strip(),
                property_type=str(r.get("property_type") or "").strip(),
                land_area=self._clean_float(r.get("land_area")),
                building_area=self._clean_float(r.get("building_area")),
                currency="KRW",
                mortgage_amount=self._clean_amount(r.get("mortgage_amount_krw")),
                senior_burden_total=self._clean_amount(r.get("senior_burden_total")),
                kb_market_price=self._clean_amount(r.get("kb_market_price")),
                appraisal_type=str(r.get("appraisal_type") or "").strip(),
                appraisal_date=self._clean_date(r.get("appraisal_date")),
                appraiser=str(r.get("appraiser") or "").strip(),
                land_value=self._clean_amount(r.get("land_value")),
                building_value=self._clean_amount(r.get("building_value")),
                machine_value=self._clean_amount(r.get("machine_value")),
                outside_value=self._clean_amount(r.get("outside_value")),
                total_value=self._clean_amount(r.get("total_value")),
                is_filed=self._parse_filed(r.get("is_filed")),
                court=str(r.get("court") or "").strip(),
                creditor=str(r.get("creditor") or "").strip(),
                case_number=str(r.get("case_number") or "").strip(),
                filing_date=self._clean_date(r.get("filing_date")),
                demand_deadline=self._clean_date(r.get("demand_deadline")),
                claim_amount=self._clean_amount(r.get("claim_amount")),
                first_legal_price=self._clean_amount(r.get("first_legal_price")),
                first_auction_date=self._clean_date(r.get("first_auction_date")),
                lapse_count=self._parse_lapse(r.get("lapse_count_raw")),
                final_result=str(r.get("final_result") or "").strip(),
                final_auction_date=self._clean_date(r.get("final_auction_date")),
                next_auction_date=self._clean_date(r.get("next_auction_date")),
                hammer_price=self._clean_amount(r.get("hammer_price")),
                final_min_bid=self._clean_amount(r.get("final_min_bid")),
                next_min_bid=self._clean_amount(r.get("next_min_bid")),
            )
            prop.property_category = self._infer_category(prop.property_type)
            prop.address_full = " ".join(filter(None, [
                prop.address_sido, prop.address_sigungu,
                prop.address_dong, prop.address_detail,
            ]))

            debtors[debtor_serial].properties.append(prop)

        deal.debtors = list(debtors.values())
