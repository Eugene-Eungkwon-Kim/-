#!/usr/bin/env python3
"""
Phase 7: 시세 그라운딩(비교사례 기반) AVM
목표: 예측가가 실거래가 ±3% 이내에 들어가는 비율 95% (T1: 비교사례 충분 물건)

방법:
  1. RTMS 마트(158,780건)에서 시간분할: 최근 2개월 = 테스트
  2. 월별 지역 가격지수 산출 (시점 보정)
  3. 동일단지 + 유사면적 비교사례의 시점보정 단가 중앙값으로 예측
  4. 층 보정 + 잔차 보정
  5. Tier별(T1: 동일단지·동일면적 / T2: 완화 매칭) ±3% 달성률 보고
"""

import sys
from pathlib import Path
import logging
import numpy as np
import pandas as pd
import duckdb
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MART = r"D:\loan4u_avm_data\loan4u_working_db\db\loan4u_rtms_comparable_mart.duckdb"
project_root = Path(__file__).parent.parent

TEST_FROM = 202605  # 테스트: 2026-05 ~ 2026-06 (최근 2개월)


def load_data():
    con = duckdb.connect(MART, read_only=True)
    df = con.execute("""
        SELECT lawd_cd, umd_nm, complex_name_norm, jibun_norm,
               exclusive_area_sqm, area_band, floor_number, floor_band,
               build_year, CAST(deal_ymd AS INTEGER) AS deal_ym,
               sale_price_krw, price_per_sqm, transaction_type
        FROM rtms_comparable_mart
        WHERE sale_price_krw > 0 AND exclusive_area_sqm > 0
    """).df()
    con.close()
    return df


def build_time_index(train):
    """시군구×월 중앙 단가 지수 (희소 시 시도 단위, 전국 단위 fallback)"""
    train = train.copy()
    train['sido'] = train['lawd_cd'].astype(str).str[:2]

    g_gu = train.groupby(['lawd_cd', 'deal_ym'])['price_per_sqm'].median()
    g_sido = train.groupby(['sido', 'deal_ym'])['price_per_sqm'].median()
    g_nat = train.groupby('deal_ym')['price_per_sqm'].median()
    return g_gu, g_sido, g_nat


def index_value(lawd, ym, g_gu, g_sido, g_nat):
    v = g_gu.get((lawd, ym))
    if v is not None and not np.isnan(v):
        return v
    v = g_sido.get((str(lawd)[:2], ym))
    if v is not None and not np.isnan(v):
        return v
    return g_nat.get(ym, np.nan)


def main():
    logger.info("=" * 60)
    logger.info("Phase 7: Comparable-Grounded AVM")
    logger.info("=" * 60)

    df = load_data()
    logger.info(f"Loaded {len(df):,} transactions")

    train = df[df['deal_ym'] < TEST_FROM].copy()
    test = df[df['deal_ym'] >= TEST_FROM].copy()
    logger.info(f"Train (< {TEST_FROM}): {len(train):,} / Test (>= {TEST_FROM}): {len(test):,}")

    g_gu, g_sido, g_nat = build_time_index(train)

    # 전국 월별 지수 (시점 보정 비율용) - 시군구 단위 우선
    # 층 보정 계수: 단지 무관 글로벌 (저층 할인 등) - train에서 floor_band별 상대 단가
    fb = train.groupby('floor_band')['price_per_sqm'].median()
    fb_rel = fb / fb.median()

    # 비교사례 인덱스: 단지 키별로 train 그룹화
    train_g = {k: v for k, v in train.groupby(['lawd_cd', 'complex_name_norm'])}

    results = []
    for row in test.itertuples():
        key = (row.lawd_cd, row.complex_name_norm)
        comps_all = train_g.get(key)
        tier = None
        pred = np.nan
        n_comps = 0

        if comps_all is not None:
            # T1: 동일단지 + 면적 ±3sqm
            comps = comps_all[(comps_all['exclusive_area_sqm'] - row.exclusive_area_sqm).abs() <= 3.0]
            if len(comps) >= 2:
                tier = 'T1'
            else:
                # T2: 동일단지 + 동일 면적밴드 (또는 ±10sqm)
                comps = comps_all[(comps_all['exclusive_area_sqm'] - row.exclusive_area_sqm).abs() <= 10.0]
                if len(comps) >= 2:
                    tier = 'T2'

            if tier:
                n_comps = len(comps)
                # 시점 보정: comp 단가 * (테스트월 지수 / comp월 지수)
                tgt_idx = index_value(row.lawd_cd, row.deal_ym, g_gu, g_sido, g_nat)
                adj_pps = []
                for c in comps.itertuples():
                    src_idx = index_value(c.lawd_cd, c.deal_ym, g_gu, g_sido, g_nat)
                    ratio = (tgt_idx / src_idx) if (src_idx and tgt_idx and not np.isnan(src_idx) and not np.isnan(tgt_idx) and src_idx > 0) else 1.0
                    ratio = min(max(ratio, 0.85), 1.15)  # 과도 보정 방지
                    # 층 보정: comp 층 -> 대상 층
                    f_src = fb_rel.get(c.floor_band, 1.0)
                    f_tgt = fb_rel.get(row.floor_band, 1.0)
                    adj_pps.append(c.price_per_sqm * ratio * (f_tgt / f_src))
                pred = float(np.median(adj_pps)) * row.exclusive_area_sqm

        if tier is None:
            tier = 'T3'  # 비교사례 부족 — 커버리지 외

        results.append((tier, n_comps, row.sale_price_krw, pred))

    res = pd.DataFrame(results, columns=['tier', 'n_comps', 'actual', 'pred'])

    logger.info("\n" + "=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)

    report_lines = []
    report_lines.append("# Phase 7 최종 보고서: 비교사례 기반 AVM ±3% 달성률\n")
    report_lines.append(f"작성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    report_lines.append(f"- 데이터: RTMS 실거래 마트 {len(df):,}건 (2025-05 ~ 2026-06)")
    report_lines.append(f"- 검증: 시간분할 (테스트 = {TEST_FROM} 이후 {len(test):,}건, 누수 없음)\n")
    report_lines.append("| Tier | 건수 | 커버리지 | ±3% | ±5% | ±10% | MAPE | 중앙오차 |")
    report_lines.append("|------|------|---------|------|------|------|------|---------|")

    summary = {}
    for tier in ['T1', 'T2', 'T3']:
        sub = res[res['tier'] == tier]
        cov = 100 * len(sub) / len(res)
        if tier == 'T3' or len(sub) == 0:
            report_lines.append(f"| {tier} (예측불가) | {len(sub):,} | {cov:.1f}% | - | - | - | - | - |")
            logger.info(f"{tier}: {len(sub):,} rows ({cov:.1f}%) — no prediction")
            continue
        err = (sub['pred'] - sub['actual']).abs() / sub['actual'] * 100
        w3, w5, w10 = (err <= 3).mean() * 100, (err <= 5).mean() * 100, (err <= 10).mean() * 100
        mape, med = err.mean(), err.median()
        summary[tier] = dict(n=len(sub), cov=cov, w3=w3, w5=w5, w10=w10, mape=mape)
        report_lines.append(f"| {tier} | {len(sub):,} | {cov:.1f}% | **{w3:.1f}%** | {w5:.1f}% | {w10:.1f}% | {mape:.2f}% | {med:.2f}% |")
        logger.info(f"{tier}: n={len(sub):,} cov={cov:.1f}% | within3%={w3:.1f}% 5%={w5:.1f}% 10%={w10:.1f}% | MAPE={mape:.2f}%")

    # 종합 (T1+T2)
    pred_sub = res[res['tier'].isin(['T1', 'T2'])]
    err_all = (pred_sub['pred'] - pred_sub['actual']).abs() / pred_sub['actual'] * 100
    w3a = (err_all <= 3).mean() * 100
    report_lines.append(f"\n## 종합 (T1+T2 예측 가능 물건)")
    report_lines.append(f"- 예측 커버리지: {100*len(pred_sub)/len(res):.1f}%")
    report_lines.append(f"- ±3% 달성률: {w3a:.1f}%, MAPE: {err_all.mean():.2f}%")

    t1 = summary.get('T1', {})
    report_lines.append(f"\n## 목표 판정")
    if t1.get('w3', 0) >= 95:
        report_lines.append(f"- ✅ T1 ±3% {t1['w3']:.1f}% — **95% 목표 달성**")
    else:
        report_lines.append(f"- T1 ±3% {t1.get('w3', 0):.1f}% — 95% 대비 갭 {95 - t1.get('w3', 0):.1f}%p")
        report_lines.append(f"- 갭 해소 방안: 비교사례 최소 건수 상향, 최근 거래 가중, 동·향 정보 추가")

    report_path = project_root / 'results' / 'phase7_final_report.md'
    report_path.write_text("\n".join(report_lines), encoding='utf-8')
    logger.info(f"\nReport saved: {report_path}")

    # 예측 상세 저장
    res.to_csv(project_root / 'results' / 'phase7_predictions.csv', index=False)
    return res, summary


if __name__ == "__main__":
    main()
