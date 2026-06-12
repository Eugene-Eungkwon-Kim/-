"""
KB Data Disk 파서 (감정평가대상목록 형식)
시트: 평가대상(물건기준)
헤더: Row 7 (0-based index 6)
데이터: Row 8 이후
"""
import re
from pathlib import Path
import openpyxl

from app.parsers.base_parser import BaseParser, DealRecord, DebtorRecord, PropertyRecord

# 헤더 키워드 → 필드명 (KB 파일 컬럼 자동 감지)
KB_HEADER_KEYWORDS = {
    "일련번호": "serial_no",
    "채권구분": "debtor_type",
    "차주일련번호": "debtor_serial",
    "차주명(실명)": "debtor_name_real",
    "차주명(비실명)": "debtor_name",
    "건전성여신잔액": "loan_balance",
    "Property Code": "property_serial",
    "담보소재지1": "address_sido",
    "담보소재지2": "address_sigungu",
    "담보소재지3": "address_dong",
    "담보소재지4": "address_detail",
    "물건용도": "property_type",
    "기계기구담보": "has_machine",
    "감정평가구분": "appraisal_type",
    "중복여부": "is_duplicate",
    "감정평가일": "appraisal_date",
    "감정평가기관": "appraiser",
    "감정평가액\n대지": "land_value",
    "감정평가액\n건물": "building_value",
    "감정평가액\n제시외면적": "outside_value",
    "감정평가액\n기계기구": "machine_value",
    "감정평가액\n합계": "total_value",
}

# 헤더가 한 셀에 여러 줄로 합쳐진 경우 부분 매칭 키워드
KB_PARTIAL_KEYWORDS = {
    "대지": "land_value",
    "건물": "building_value",
    "제시외면적": "outside_value",
    "기계기구 등": "machine_value",
    "합계": "total_value",
}


class KBParser(BaseParser):

    # 가격입력시트 컬럼 키워드 (감정가 포함된 완성 시트)
    PRICE_SHEET_KEYWORDS = {
        "일련번호": "serial_no",
        "채권구분": "debtor_type",
        "차주일련번호": "debtor_serial",
        "차주명": "debtor_name",
        "Property #": "property_code",
        "Lien #": "lien_no",
        "담보소재지1": "address_sido",
        "담보소재지2": "address_sigungu",
        "담보소재지3": "address_dong",
        "담보소재지4": "address_detail",
        "등기부등본용도": "property_type",
        "대지면적": "land_area",
        "건물면적": "building_area",
        "감정평가일": "appraisal_date",
        "감정평가기관": "appraiser",
        "감정평가액\n대지": "land_value",
        "감정평가액\n건물": "building_value",
        "감정평가액\n제시외": "outside_value",
        "감정평가액\n기계기구": "machine_value",
        "감정평가액\n합계": "total_value",
    }

    def parse(self, file_path: str) -> DealRecord:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
        deal = self._parse_meta(wb, file_path)

        # 가격입력시트 우선 (감정가 포함), 없으면 담보(물건) 또는 평가대상 시트
        if "가격입력시트" in wb.sheetnames:
            self._parse_price_sheet(wb["가격입력시트"], deal)
        else:
            sheet_name = None
            # KB 2025-4+ 형식: "3. 담보(물건)"
            for candidate in ["3. 담보(물건)", "담보(물건)", "평가대상(물건기준)", "Sheet1", "물건기준"]:
                if candidate in wb.sheetnames:
                    sheet_name = candidate
                    break
            if sheet_name is None:
                sheet_name = wb.sheetnames[0]

            # "담보(물건)" 시트는 다른 구조 (Row 9 헤더, Row 10 데이터)
            if "담보" in sheet_name:
                self._parse_property_sheet_kb2025(wb[sheet_name], deal)
            else:
                self._parse_properties(wb[sheet_name], deal)

        wb.close()
        return deal

    def _parse_price_sheet(self, ws, deal: DealRecord):
        """가격입력시트: 완성된 감정가 + 물건정보"""
        col_map = {}
        for row in ws.iter_rows(min_row=1, max_row=12, values_only=True):
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                for kw, field in self.PRICE_SHEET_KEYWORDS.items():
                    if kw in cell_str and field not in col_map:
                        col_map[field] = idx
                # 부분 매칭 (감정평가액 하위)
                for kw, field in KB_PARTIAL_KEYWORDS.items():
                    if kw in cell_str and field not in col_map:
                        col_map[field] = idx
            if len(col_map) >= 15:
                break

        data_start = self._find_data_start(ws)
        debtors: dict[str, DebtorRecord] = {}

        for row in ws.iter_rows(min_row=data_start, values_only=True):
            if not any(row):
                continue

            def g(field):
                idx = col_map.get(field)
                return row[idx] if idx is not None and idx < len(row) else None

            debtor_serial = str(g("debtor_serial") or "").strip()
            if not debtor_serial:
                continue

            # property_serial = Property# + Lien# 조합
            prop_code = str(g("property_code") or "").strip()
            lien_no = str(g("lien_no") or "").strip()
            prop_serial = f"{prop_code}-{lien_no}" if lien_no else prop_code

            if debtor_serial not in debtors:
                debtors[debtor_serial] = DebtorRecord(
                    debtor_serial=debtor_serial,
                    debtor_name=str(g("debtor_name") or "").strip(),
                    debtor_type=str(g("debtor_type") or "Regular").strip(),
                    pool_class="A",
                )

            prop = PropertyRecord(
                property_serial=prop_serial,
                address_sido=str(g("address_sido") or "").strip(),
                address_sigungu=str(g("address_sigungu") or "").strip(),
                address_dong=str(g("address_dong") or "").strip(),
                address_detail=str(g("address_detail") or "").strip(),
                property_type=str(g("property_type") or "").strip(),
                land_area=self._clean_float(g("land_area")),
                building_area=self._clean_float(g("building_area")),
                appraisal_date=self._clean_date(g("appraisal_date")),
                appraiser=str(g("appraiser") or "").strip(),
                land_value=self._clean_amount(g("land_value")),
                building_value=self._clean_amount(g("building_value")),
                machine_value=self._clean_amount(g("machine_value")),
                outside_value=self._clean_amount(g("outside_value")),
                total_value=self._clean_amount(g("total_value")),
            )
            prop.property_category = self._infer_category(prop.property_type)
            prop.address_full = " ".join(filter(None, [
                prop.address_sido, prop.address_sigungu,
                prop.address_dong, prop.address_detail,
            ]))
            debtors[debtor_serial].properties.append(prop)

        deal.debtors = list(debtors.values())

    def _parse_meta(self, wb, file_path: str) -> DealRecord:
        deal = DealRecord(source_file=file_path, financial_institution="KB")
        stem = Path(file_path).stem
        m = re.search(r"KB[\s_]*(\d{4}-\d+[\w.]*)", stem, re.IGNORECASE)
        if m:
            deal.deal_name = f"KB {m.group(1)} Program"
        else:
            deal.deal_name = stem[:60]

        # 딜명에서 pool 추출
        pm = re.search(r"Pool\s*([A-Z])", stem, re.IGNORECASE)
        deal.pool_name = f"Pool {pm.group(1).upper()}" if pm else "Pool A"
        return deal

    def _build_col_map(self, ws) -> dict[str, int]:
        col_map = {}
        for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                # 정확 매칭
                for kw, field in KB_HEADER_KEYWORDS.items():
                    if kw in cell_str and field not in col_map:
                        col_map[field] = idx
                # 부분 매칭 (감정평가액 하위)
                if "감정평가액" in cell_str or "감정가" in cell_str:
                    for kw, field in KB_PARTIAL_KEYWORDS.items():
                        if kw in cell_str and field not in col_map:
                            col_map[field] = idx
            if len(col_map) >= 15:
                break
        return col_map

    def _find_data_start(self, ws) -> int:
        for row_idx, row in enumerate(ws.iter_rows(min_row=5, max_row=15, values_only=True), start=5):
            if row and len(row) > 1 and row[1] is not None:
                try:
                    int(float(str(row[1]).replace(",", "")))
                    return row_idx
                except (ValueError, TypeError):
                    pass
        return 8

    def _parse_properties(self, ws, deal: DealRecord):
        col_map = self._build_col_map(ws)
        data_start = self._find_data_start(ws)
        debtors: dict[str, DebtorRecord] = {}

        for row in ws.iter_rows(min_row=data_start, values_only=True):
            if not any(row):
                continue
            debtor_serial_idx = col_map.get("debtor_serial")
            if debtor_serial_idx is None or debtor_serial_idx >= len(row):
                continue
            debtor_serial = str(row[debtor_serial_idx] or "").strip()
            if not debtor_serial:
                continue

            def g(field):
                idx = col_map.get(field)
                return row[idx] if idx is not None and idx < len(row) else None

            if debtor_serial not in debtors:
                debtors[debtor_serial] = DebtorRecord(
                    debtor_serial=debtor_serial,
                    debtor_name=str(g("debtor_name") or g("debtor_name_real") or "").strip(),
                    debtor_type=str(g("debtor_type") or "Regular").strip(),
                    pool_class="A",
                )

            prop = PropertyRecord(
                property_serial=str(g("property_serial") or "").strip(),
                address_sido=str(g("address_sido") or "").strip(),
                address_sigungu=str(g("address_sigungu") or "").strip(),
                address_dong=str(g("address_dong") or "").strip(),
                address_detail=str(g("address_detail") or "").strip(),
                property_type=str(g("property_type") or "").strip(),
                appraisal_type=str(g("appraisal_type") or "").strip(),
                appraisal_date=self._clean_date(g("appraisal_date")),
                appraiser=str(g("appraiser") or "").strip(),
                land_value=self._clean_amount(g("land_value")),
                building_value=self._clean_amount(g("building_value")),
                machine_value=self._clean_amount(g("machine_value")),
                outside_value=self._clean_amount(g("outside_value")),
                total_value=self._clean_amount(g("total_value")),
            )
            prop.property_category = self._infer_category(prop.property_type)
            prop.address_full = " ".join(filter(None, [
                prop.address_sido, prop.address_sigungu,
                prop.address_dong, prop.address_detail,
            ]))
            debtors[debtor_serial].properties.append(prop)

        deal.debtors = list(debtors.values())

    def _parse_property_sheet_kb2025(self, ws, deal: DealRecord):
        """KB 2025-4+ 형식: '담보(물건)' 시트 파싱 (Row 9=헤더, Row 10=데이터)"""
        # Row 9에서 헤더 인식
        header_row = list(ws.iter_rows(min_row=9, max_row=9, values_only=True))[0]
        col_map = {}

        for idx, cell in enumerate(header_row):
            if cell is None:
                continue
            cell_str = str(cell).strip()

            # KB 2025-4 컬럼 매핑
            mapping = {
                "일련번호": "serial_no",
                "Pool": "pool_class",
                "자산구분": "debtor_type",
                "차주일련번호": "debtor_serial",
                "차주명": "debtor_name",
                "물건번호": "property_serial",
                "담보소재지1": "address_sido",
                "담보소재지2": "address_sigungu",
                "담보소재지3": "address_dong",
                "담보소재지4": "address_detail",
                "Property Type": "property_type",
                "대지면적": "land_area",
                "건물면적": "building_area",
                "감정평가일": "appraisal_date",
                "감정평가기관": "appraiser",
                "감정평가액\n토지": "land_value",
                "감정평가액\n건물": "building_value",
                "감정평가액\n기계기구": "machine_value",
                "감정평가액\n기타": "outside_value",
                "감정평가액\n합계": "total_value",
                "감정평가서 종류": "appraisal_type",
            }

            for kw, field in mapping.items():
                if kw in cell_str and field not in col_map:
                    col_map[field] = idx

        debtors: dict[str, DebtorRecord] = {}

        # Row 10부터 데이터 파싱
        for row in ws.iter_rows(min_row=10, values_only=True):
            if not any(row):
                continue

            def g(field):
                idx = col_map.get(field)
                return row[idx] if idx is not None and idx < len(row) else None

            debtor_serial = str(g("debtor_serial") or "").strip()
            if not debtor_serial:
                continue

            # Debtor 기록
            if debtor_serial not in debtors:
                debtor = DebtorRecord(
                    debtor_serial=debtor_serial,
                    debtor_name=str(g("debtor_name") or "").strip(),
                    debtor_type=str(g("debtor_type") or "").strip(),
                    pool_class=str(g("pool_class") or "").strip(),
                    properties=[],
                )
                debtors[debtor_serial] = debtor

            # Property 기록
            property_serial = str(g("property_serial") or "").strip()
            if property_serial:
                prop = PropertyRecord(
                    property_serial=property_serial,
                    address_sido=str(g("address_sido") or "").strip(),
                    address_sigungu=str(g("address_sigungu") or "").strip(),
                    address_dong=str(g("address_dong") or "").strip(),
                    address_detail=str(g("address_detail") or "").strip(),
                    land_area=self._clean_amount(g("land_area")),
                    building_area=self._clean_amount(g("building_area")),
                    property_type=str(g("property_type") or "").strip(),
                    appraisal_type=str(g("appraisal_type") or "").strip(),
                    appraisal_date=self._clean_date(g("appraisal_date")),
                    appraiser=str(g("appraiser") or "").strip(),
                    land_value=self._clean_amount(g("land_value")),
                    building_value=self._clean_amount(g("building_value")),
                    machine_value=self._clean_amount(g("machine_value")),
                    outside_value=self._clean_amount(g("outside_value")),
                    total_value=self._clean_amount(g("total_value")),
                )
                prop.property_category = self._infer_category(prop.property_type)
                prop.address_full = " ".join(filter(None, [
                    prop.address_sido, prop.address_sigungu,
                    prop.address_dong, prop.address_detail,
                ]))
                debtors[debtor_serial].properties.append(prop)

        deal.debtors = list(debtors.values())
