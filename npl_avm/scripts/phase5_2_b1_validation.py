#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5-2 B1: 이상탐지 엔진 검증 스크립트
검증 항목: 데이터 완성도, 이상탐지 성능, 응답 시간, 신뢰도
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.monitoring.npl_anomaly_detector import NPLAnomalyDetector
from app.db.models import Auction


def validate_data_completeness(session, batch_size=500):
    """데이터 완성도 검증"""
    logger.info("=" * 80)
    logger.info("[검증 1] 데이터 완성도")
    logger.info("=" * 80)

    try:
        # 총 레코드 수
        total_records = session.query(Auction).count()
        logger.info(f"총 레코드: {total_records}개")

        # 결측값 체크
        records_with_null = 0
        records_with_outliers = 0

        batches = (total_records // batch_size) + 1
        for i in range(batches):
            offset = i * batch_size
            batch = session.query(Auction).offset(offset).limit(batch_size).all()

            for record in batch:
                # 핵심 필드 결측 체크
                if not record.appraisal_value or not record.hammer_price or not record.hammer_rate:
                    records_with_null += 1

                # 이상치 체크 (낙찰가율 0-200%)
                if record.hammer_rate and (record.hammer_rate < 0 or record.hammer_rate > 2.0):
                    records_with_outliers += 1

        missing_rate = (records_with_null / total_records) * 100
        outlier_rate = (records_with_outliers / total_records) * 100

        logger.info(f"결측값: {records_with_null}개 ({missing_rate:.2f}%)")
        logger.info(f"이상치: {records_with_outliers}개 ({outlier_rate:.2f}%)")

        # 검증 기준
        missing_ok = missing_rate < 1.0
        outlier_ok = outlier_rate < 2.0

        logger.info(f"결측값 검증: {'✅ PASS' if missing_ok else '❌ FAIL'}")
        logger.info(f"이상치 검증: {'✅ PASS' if outlier_ok else '❌ FAIL'}")

        return missing_ok and outlier_ok

    except Exception as e:
        logger.error(f"데이터 검증 오류: {e}")
        return False


def validate_anomaly_detection(session, sample_size=100):
    """이상탐지 엔진 성능 검증"""
    logger.info("\n" + "=" * 80)
    logger.info("[검증 2] 이상탐지 엔진 성능")
    logger.info("=" * 80)

    try:
        detector = NPLAnomalyDetector()

        # 샘플 데이터 로드
        auctions = session.query(Auction).limit(sample_size).all()

        logger.info(f"샘플 데이터: {len(auctions)}개 물건")

        # IQR 감지
        hammer_rates = [a.hammer_rate for a in auctions if a.hammer_rate]
        anomalies_iqr, rate_iqr = detector.detect_by_iqr(hammer_rates)
        logger.info(f"✅ IQR 감지: {len(anomalies_iqr)}개 (감지율: {rate_iqr:.1%})")

        # Z-score 감지
        anomalies_z, rate_z = detector.detect_by_zscore(hammer_rates)
        logger.info(f"✅ Z-score 감지: {len(anomalies_z)}개 (감지율: {rate_z:.1%})")

        # 통합 판정 (predict_anomaly)
        anomalies_detected = 0
        confidence_scores = []

        for auction in auctions[:20]:  # 20개 샘플 테스트
            result = detector.predict_anomaly(
                hammer_rate=auction.hammer_rate or 0.7,
                property_id=auction.property_id,
                appraisal_value=auction.appraisal_value or 500000000,
                hammer_price=auction.hammer_price or 350000000,
                property_type="아파트",
                address_sido="서울"
            )

            if result['is_anomaly']:
                anomalies_detected += 1
            confidence_scores.append(result['confidence'])

        overall_detection_rate = (anomalies_detected / 20) * 100
        avg_confidence = np.mean(confidence_scores)

        logger.info(f"✅ 통합 판정: {anomalies_detected}개 이상 (감지율: {overall_detection_rate:.1%})")
        logger.info(f"✅ 평균 신뢰도: {avg_confidence:.2%}")

        # 성능 기준 (감지율 5%+, 평균 신뢰도 30%+)
        detection_ok = overall_detection_rate >= 5.0
        confidence_ok = avg_confidence >= 0.3

        logger.info(f"감지율 검증: {'✅ PASS' if detection_ok else '⚠️ 낮음'}")
        logger.info(f"신뢰도 검증: {'✅ PASS' if confidence_ok else '⚠️ 낮음'}")

        return detection_ok and confidence_ok

    except Exception as e:
        logger.error(f"이상탐지 검증 오류: {e}")
        return False


def validate_response_time(session, iterations=100):
    """응답 시간 검증"""
    logger.info("\n" + "=" * 80)
    logger.info("[검증 3] 응답 시간")
    logger.info("=" * 80)

    try:
        detector = NPLAnomalyDetector()
        auctions = session.query(Auction).limit(iterations).all()

        response_times = []

        for auction in auctions:
            start = time.time()

            result = detector.predict_anomaly(
                hammer_rate=auction.hammer_rate or 0.7,
                property_id=auction.property_id,
                appraisal_value=auction.appraisal_value or 500000000,
                hammer_price=auction.hammer_price or 350000000,
                property_type="아파트",
                address_sido="서울"
            )

            elapsed_ms = (time.time() - start) * 1000
            response_times.append(elapsed_ms)

        response_times = np.array(response_times)

        mean_time = response_times.mean()
        p95_time = np.percentile(response_times, 95)
        p99_time = np.percentile(response_times, 99)

        logger.info(f"평균 응답시간: {mean_time:.2f}ms")
        logger.info(f"P95 응답시간: {p95_time:.2f}ms")
        logger.info(f"P99 응답시간: {p99_time:.2f}ms")

        # 기준: P95 <100ms
        time_ok = p95_time < 100.0

        logger.info(f"응답시간 검증 (P95 <100ms): {'✅ PASS' if time_ok else '❌ FAIL'}")

        return time_ok

    except Exception as e:
        logger.error(f"응답시간 검증 오류: {e}")
        return False


def validate_confidence_calibration():
    """신뢰도 교정 검증"""
    logger.info("\n" + "=" * 80)
    logger.info("[검증 4] 신뢰도 교정")
    logger.info("=" * 80)

    try:
        detector = NPLAnomalyDetector()

        # 테스트 케이스: 정상, 의심, 이상
        test_cases = [
            {
                "name": "정상 거래",
                "hammer_rate": 0.8,
                "property_type": "아파트",
                "expected_anomaly": False
            },
            {
                "name": "의심 거래",
                "hammer_rate": 0.5,
                "property_type": "아파트",
                "expected_anomaly": True
            },
            {
                "name": "이상 거래",
                "hammer_rate": 0.2,
                "property_type": "아파트",
                "expected_anomaly": True
            }
        ]

        correct_predictions = 0

        for case in test_cases:
            result = detector.predict_anomaly(
                hammer_rate=case["hammer_rate"],
                property_id=1,
                appraisal_value=500000000,
                hammer_price=case["hammer_rate"] * 500000000,
                property_type=case["property_type"],
                address_sido="서울"
            )

            is_correct = result['is_anomaly'] == case['expected_anomaly']
            correct_predictions += is_correct

            status = "✅" if is_correct else "❌"
            logger.info(f"{status} {case['name']}: {result['anomaly_score']}점, " +
                       f"신뢰도 {result['confidence']:.1%}")

        accuracy = (correct_predictions / len(test_cases)) * 100
        logger.info(f"신뢰도 교정 정확도: {accuracy:.1f}%")

        return accuracy >= 66.7  # 2/3 이상 정확

    except Exception as e:
        logger.error(f"신뢰도 교정 검증 오류: {e}")
        return False


def main():
    """메인 검증 함수"""
    logger.info("\n" + "=" * 80)
    logger.info("Phase 5-2 B1: 이상탐지 엔진 검증 시작")
    logger.info("=" * 80)

    start_time = datetime.now()

    # DB 연결
    try:
        engine = create_engine("sqlite:///data/npl_avm.db")
        Session = sessionmaker(bind=engine)
        session = Session()

        # 검증 실행
        results = {
            "데이터 완성도": validate_data_completeness(session),
            "이상탐지 성능": validate_anomaly_detection(session),
            "응답 시간": validate_response_time(session),
            "신뢰도 교정": validate_confidence_calibration()
        }

        # 최종 결과
        logger.info("\n" + "=" * 80)
        logger.info("[최종 검증 결과]")
        logger.info("=" * 80)

        all_pass = True
        for item, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{item}: {status}")
            all_pass = all_pass and result

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n검증 소요 시간: {elapsed:.1f}초")

        # 최종 판정
        logger.info("\n" + "=" * 80)
        if all_pass:
            logger.info("🎉 B1 검증 완료: 모든 기준 충족 ✅")
            logger.info("Day 2 B1 API 구현 진행 가능")
        else:
            logger.info("⚠️ B1 검증: 일부 항목 미달")
            logger.info("미달 항목에 대한 개선 필요")
        logger.info("=" * 80)

        session.close()
        return 0 if all_pass else 1

    except Exception as e:
        logger.error(f"검증 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
