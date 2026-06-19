#!/usr/bin/env python3
"""
Weekly Performance Monitor for AVM Models
매주 모델 성능을 모니터링하고 알림을 전송합니다.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

script_dir = Path(__file__).parent.parent
log_dir = script_dir / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'performance_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """모델 성능 모니터 및 알림 시스템"""

    def __init__(self, config_path=None):
        """초기화"""
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'config' / 'schedule_config.json'

        self.config_path = config_path
        self.project_root = Path(__file__).parent.parent
        self.config = self._load_config()
        log_file_path = self.config.get('log_file', 'logs/retrain_history.jsonl')
        self.log_file = self.project_root / log_file_path
        self.alert_config = self.config.get('alert_config', {})

    def _load_config(self):
        """설정 파일 로드"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일 없음: {self.config_path}. 기본값 사용")
            return self._get_default_config()

    def _get_default_config(self):
        """기본 설정"""
        return {
            'performance_threshold': 0.95,
            'rmse_threshold': 60000000,
            'alert_config': {
                'enable_email': False,
                'enable_slack': False,
                'email_address': None,
                'slack_webhook': None
            },
            'log_file': 'avm_project/logs/retrain_history.jsonl'
        }

    def load_history(self, num_records=10):
        """재학습 기록 로드"""
        if not self.log_file.exists():
            logger.info("재학습 기록 없음")
            return []

        try:
            records = []
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return records[-num_records:]
        except Exception as e:
            logger.error(f"기록 로드 실패: {e}")
            return []

    def calculate_trend(self, records, metric='r2'):
        """성능 추세 계산"""
        if not records or len(records) < 2:
            return None

        try:
            values = []
            for record in records:
                if metric == 'r2':
                    ensemble_r2 = record.get('ensemble', {}).get('r2')
                    if ensemble_r2:
                        values.append(ensemble_r2)
                elif metric == 'rmse':
                    ensemble_rmse = record.get('ensemble', {}).get('rmse')
                    if ensemble_rmse:
                        values.append(ensemble_rmse)

            if len(values) < 2:
                return None

            # 선형 회귀로 추세 계산
            x = np.arange(len(values))
            coeffs = np.polyfit(x, values, 1)
            trend_direction = "↑ 상승" if coeffs[0] > 0 else "↓ 하락"
            trend_rate = abs(coeffs[0]) * 100

            return {
                'direction': trend_direction,
                'rate': trend_rate,
                'latest': values[-1],
                'previous': values[-2] if len(values) > 1 else None
            }

        except Exception as e:
            logger.warning(f"추세 계산 실패: {e}")
            return None

    def check_alerts(self, latest_record):
        """알림 필요 여부 확인"""
        alerts = []

        if not latest_record:
            return alerts

        # R² 저하 확인
        r2_threshold = self.config.get('performance_threshold', 0.95)
        ensemble_r2 = latest_record.get('ensemble', {}).get('r2', 0)

        if ensemble_r2 < 0.80:
            alerts.append({
                'type': 'critical',
                'message': f"⚠️ CRITICAL: R² = {ensemble_r2:.4f} (기준값: {r2_threshold:.2f})",
                'severity': 'high'
            })
        elif ensemble_r2 < r2_threshold:
            alerts.append({
                'type': 'warning',
                'message': f"⚠️ WARNING: R² = {ensemble_r2:.4f} (기준값: {r2_threshold:.2f})",
                'severity': 'medium'
            })

        # RMSE 증가 확인
        rmse_threshold = self.config.get('rmse_threshold', 60000000)
        ensemble_rmse = latest_record.get('ensemble', {}).get('rmse', 0)

        if ensemble_rmse > rmse_threshold:
            alerts.append({
                'type': 'rmse_warning',
                'message': f"⚠️ RMSE 증가: {ensemble_rmse:,.0f}원 (기준값: {rmse_threshold:,.0f})",
                'severity': 'medium'
            })

        # 학습 실패 확인
        if latest_record.get('status') == 'failed':
            alerts.append({
                'type': 'failure',
                'message': f"❌ 학습 실패",
                'severity': 'high'
            })

        return alerts

    def generate_report(self):
        """성능 리포트 생성"""
        logger.info("=" * 80)
        logger.info("📊 성능 모니터링 리포트")
        logger.info("=" * 80)

        records = self.load_history(num_records=10)

        if not records:
            logger.info("재학습 기록 없음")
            return

        # 최신 기록
        latest = records[-1]
        timestamp = latest.get('timestamp', 'N/A')
        status = latest.get('status', 'unknown')

        logger.info(f"\n✅ 최신 재학습: {timestamp}")
        logger.info(f"상태: {status.upper()}")

        # 앙상블 성능
        ensemble = latest.get('ensemble', {})
        logger.info(f"\n📈 앙상블 모델 성능:")
        logger.info(f"  R² = {ensemble.get('r2', 'N/A'):.4f}")
        logger.info(f"  RMSE = {ensemble.get('rmse', 'N/A'):,.0f}원")
        logger.info(f"  MAE = {ensemble.get('mae', 'N/A'):,.0f}원")

        # 개별 모델 성능
        models = latest.get('models', {})
        logger.info(f"\n🔧 개별 모델 성능:")
        for model_name, metrics in models.items():
            if 'error' not in metrics:
                logger.info(f"  {model_name}: R² = {metrics.get('r2', 'N/A'):.4f}")

        # 추세 분석
        r2_trend = self.calculate_trend(records, metric='r2')
        if r2_trend:
            logger.info(f"\n📊 R² 추세:")
            logger.info(f"  방향: {r2_trend['direction']}")
            logger.info(f"  변화율: {r2_trend['rate']:.2f}%")
            logger.info(f"  최신값: {r2_trend['latest']:.4f}")
            if r2_trend['previous']:
                logger.info(f"  이전값: {r2_trend['previous']:.4f}")

        # 알림
        alerts = self.check_alerts(latest)
        if alerts:
            logger.warning(f"\n🚨 알림 ({len(alerts)}개):")
            for alert in alerts:
                logger.warning(f"  [{alert['severity'].upper()}] {alert['message']}")
        else:
            logger.info("\n✅ 모든 지표 정상")

        # 통계
        logger.info(f"\n📋 통계 (최근 {len(records)}회):")
        if records:
            r2_values = [r.get('ensemble', {}).get('r2', 0) for r in records if r.get('ensemble', {}).get('r2')]
            if r2_values:
                logger.info(f"  평균 R²: {np.mean(r2_values):.4f}")
                logger.info(f"  최고 R²: {np.max(r2_values):.4f}")
                logger.info(f"  최저 R²: {np.min(r2_values):.4f}")

        logger.info("=" * 80)

    def send_email_alert(self, alerts):
        """이메일 알림 전송 (미구현)"""
        if not self.alert_config.get('enable_email'):
            return

        email = self.alert_config.get('email_address')
        if not email:
            logger.warning("이메일 주소 없음")
            return

        logger.info(f"📧 이메일 알림 전송: {email}")
        # TODO: 이메일 구현

    def send_slack_alert(self, alerts):
        """Slack 알림 전송 (미구현)"""
        if not self.alert_config.get('enable_slack'):
            return

        webhook = self.alert_config.get('slack_webhook')
        if not webhook:
            logger.warning("Slack Webhook 없음")
            return

        logger.info("💬 Slack 알림 전송")
        # TODO: Slack 구현

    def run(self):
        """모니터링 실행"""
        logger.info("🔍 성능 모니터링 시작")

        records = self.load_history()
        if records:
            latest = records[-1]
            alerts = self.check_alerts(latest)

            if alerts:
                logger.warning(f"⚠️ {len(alerts)}개 알림 발생")
                self.send_email_alert(alerts)
                self.send_slack_alert(alerts)

        self.generate_report()
        return True


def main():
    """메인 함수"""
    monitor = PerformanceMonitor()
    success = monitor.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
