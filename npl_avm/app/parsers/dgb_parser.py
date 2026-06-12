"""
DGB Data Disk 파서 (IBKParser 상속)
시트: Sheet C-1
헤더: Row 11 (키워드 자동감지, C1_FIXED 사용 안 함)
특이사항:
  - (구)감정평가 + 최근감정평가 두 섹션 → 최근 감정평가 우선
  - 주소 컬럼명: 도(시)/시(군,구)/동(읍,면,리)
  - 낙찰금액 컬럼 포함 (낙찰가율 계산 가능)
"""
import re
from pathlib import Path

from app.parsers.ibk_parser import IBKParser, C1_HEADER_KEYWORDS
from app.parsers.base_parser import DealRecord

# DGB 전용 키워드 (IBK와 다른 컬럼명)
DGB_KEYWORDS = {
    "일련번호": "serial_no",
    "채권구분": "debtor_type",
    "차주\n일련번호": "debtor_serial",
    "차주명": "debtor_name",
    "물건\n일련번호": "property_serial",
    "도(시)": "address_sido",
    "시(군,구)": "address_sigungu",
    "동(읍,면,리)": "address_dong",
    "기타 담보물건 주소지": "address_detail",
    "물건유형": "property_type",
    "대지면적": "land_area",
    "건물면적": "building_area",
    "공장저당법": "factory_mortgage",
    "적용통화": "currency",
    "환산 후 당행\n근저당권 설정액": "mortgage_amount_krw",
    "환산 후 당행": "mortgage_amount_krw",
    "선순위 가압류 등": "has_provisional_seizure",
    "선순위 임금채권": "wage_claim",
    "선순위 조세채권": "tax_claim",
    "선순위 당해세": "current_tax",
    "선순위 임차보증금(주택)": "lease_deposit_housing",
    "선순위 임차보증금(상가)": "lease_deposit_commercial",
    "선순위 소액임차보증금(주택)": "small_deposit_housing",
    "선순위 소액임차보증금(상가)": "small_deposit_commercial",
    # 최근 감정평가 (구 감정평가보다 우선)
    "최근 감정평가일": "appraisal_date",
    "최근 감정평가기관": "appraiser",
    "최근 감정평가액\n-토지": "land_value",
    "최근 감정평가액\n-건물": "building_value",
    "최근 감정평가액\n-제시외 물건": "outside_value",
    "최근 감정평가액\n-기계기구": "machine_value",
    "최근 감정평가액 합계": "total_value",
    # 경매 관련
    "경매개시 여부": "is_filed",
    "경매관할법원": "court",
    "경매사건번호\n(모사건기준)": "case_number",
    "경매신청자\n(모사건기준)": "creditor",
    "경매신청금액": "claim_amount",
    "경매개시일자": "filing_date",
    "배당요구종기일": "demand_deadline",
    "최초법사가": "first_legal_price",
    "최초경매기일": "first_auction_date",
    "최종경매회차": "lapse_count_raw",
    "최종경매기일": "final_auction_date",
    "최종경매결과": "final_result",
    "최종경매일의\n최저입찰금액": "final_min_bid",
    "최종경매일의\n낙찰금액": "hammer_price",
    "차기경매일자": "next_auction_date",
    "차기경매일의\n최저입찰금액": "next_min_bid",
}


class DGBParser(IBKParser):

    def _parse_deal_meta(self, wb, file_path: str) -> DealRecord:
        deal = DealRecord(source_file=file_path, financial_institution="DGB")
        stem = Path(file_path).stem
        m = re.search(r"DGB[\s_]*(\d{4}-\d+[\w.]*)", stem, re.IGNORECASE)
        if m:
            deal.deal_name = f"DGB {m.group(1)} Program"
        else:
            deal.deal_name = stem[:60]
        deal.pool_name = "Pool A"
        return deal

    def _build_col_map(self, ws) -> dict[str, int]:
        """C1_FIXED 무시, DGB_KEYWORDS + C1_HEADER_KEYWORDS 키워드로만 매핑"""
        col_map: dict[str, int] = {}
        all_keywords = {**DGB_KEYWORDS, **C1_HEADER_KEYWORDS}

        for row in ws.iter_rows(min_row=8, max_row=13, values_only=True):
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                for keyword, field in all_keywords.items():
                    if keyword in cell_str and field not in col_map:
                        col_map[field] = idx
            if len(col_map) >= 30:
                break

        return col_map

    def _find_data_start(self, ws) -> int:
        """DGB Row10은 Field 순번, Row11은 헤더 → 데이터는 Row12 이후"""
        for row_idx, r_obj in enumerate(ws.iter_rows(min_row=12, max_row=25), start=12):
            if len(r_obj) > 1 and r_obj[1].value is not None:
                try:
                    int(float(str(r_obj[1].value).replace(",", "")))
                    return row_idx
                except (ValueError, TypeError):
                    pass
        return 12

    def _parse_c1(self, ws, deal: DealRecord):
        """C1_FIXED 적용 없이 키워드 맵만 사용"""
        from app.parsers.base_parser import DebtorRecord, PropertyRecord
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
                d = DebtorRecord(
                    debtor_serial=debtor_serial,
                    debtor_name=str(r["debtor_name"] or "").strip(),
                    debtor_type=str(r["debtor_type"] or "Regular").strip(),
                    pool_class="A",
                )
                debtors[debtor_serial] = d

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
                currency=str(r.get("currency") or "KRW").strip(),
                mortgage_amount=self._clean_amount(r.get("mortgage_amount_krw")),
                senior_mortgage_amount=self._clean_amount(r.get("senior_mortgage_krw")),
                has_provisional_seizure=self._parse_yn(r.get("has_provisional_seizure")),
                provisional_seizure_amount=self._clean_amount(r.get("provisional_seizure_amount")),
                has_lien=self._parse_yn(r.get("has_lien")),
                lien_amount=self._clean_amount(r.get("lien_amount")),
                small_deposit_housing=self._clean_amount(r.get("small_deposit_housing")),
                small_deposit_commercial=self._clean_amount(r.get("small_deposit_commercial")),
                lease_deposit_housing=self._clean_amount(r.get("lease_deposit_housing")),
                lease_deposit_commercial=self._clean_amount(r.get("lease_deposit_commercial")),
                wage_claim=self._clean_amount(r.get("wage_claim")),
                current_tax=self._clean_amount(r.get("current_tax")),
                tax_claim=self._clean_amount(r.get("tax_claim")),
                senior_burden_total=self._clean_amount(r.get("senior_burden_total")),
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
