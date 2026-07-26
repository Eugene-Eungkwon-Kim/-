"""
재학습 모니터링 모듈
Phase D-2의 JSONL 기록 파일을 실시간으로 모니터링
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

# backend/ 는 avm_project/ 내부에 위치하므로 parent.parent == avm_project 디렉토리
AVM_PROJECT = Path(__file__).parent.parent
HISTORY_FILE = AVM_PROJECT / "logs" / "retrain_history.jsonl"
CONFIG_FILE = AVM_PROJECT / "config" / "schedule_config.json"


class AlertType(str, Enum):
    """알림 타입"""
    DEGRADATION = "degradation"
    FAILURE = "failure"
    SUCCESS = "success"
    THRESHOLD = "threshold"


class RetrainingMonitor:
    """재학습 모니터"""

    def __init__(self):
        self.history_file = HISTORY_FILE
        self.config_file = CONFIG_FILE
        self.cache: Dict[str, Any] = {}
        self.last_read_time: Optional[datetime] = None
        self.performance_threshold = 0.95
        self._load_config()

    def _load_config(self) -> None:
        """설정 로드"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.performance_threshold = config.get(
                        'performance_threshold',
                        0.95
                    )
                    logger.info(f"✅ 성능 임계값: {self.performance_threshold}")
        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")

    def get_latest_result(self) -> Optional[Dict[str, Any]]:
        """최신 재학습 결과 조회"""
        try:
            if not self.history_file.exists():
                logger.warning(f"파일 없음: {self.history_file}")
                return None

            with open(self.history_file, 'r') as f:
                lines = f.readlines()

            if not lines:
                logger.warning("재학습 기록이 없습니다")
                return None

            # 마지막 줄 파싱
            latest_line = lines[-1].strip()
            latest_result = json.loads(latest_line)

            # 캐시 저장
            self.cache['latest'] = latest_result
            self.last_read_time = datetime.now()

            logger.info(f"✅ 최신 결과 로드: {latest_result.get('timestamp')}")
            return latest_result

        except Exception as e:
            logger.error(f"❌ 최신 결과 로드 실패: {e}")
            return None

    def get_previous_result(self) -> Optional[Dict[str, Any]]:
        """이전 재학습 결과 조회"""
        try:
            if not self.history_file.exists():
                return None

            with open(self.history_file, 'r') as f:
                lines = f.readlines()

            if len(lines) < 2:
                return None

            # 마지막에서 두 번째 줄 파싱
            previous_line = lines[-2].strip()
            previous_result = json.loads(previous_line)

            return previous_result

        except Exception as e:
            logger.error(f"❌ 이전 결과 로드 실패: {e}")
            return None

    def check_performance_degradation(self) -> Optional[Dict[str, Any]]:
        """성능 저하 확인"""
        try:
            latest = self.get_latest_result()
            previous = self.get_previous_result()

            if latest is None or previous is None:
                return None

            latest_r2 = latest.get('ensemble', {}).get('r2', 0)
            previous_r2 = previous.get('ensemble', {}).get('r2', 0)

            # 성능 저하 계산
            degradation_ratio = latest_r2 / previous_r2 if previous_r2 > 0 else 1

            if degradation_ratio < self.performance_threshold:
                degradation_pct = (1 - degradation_ratio) * 100

                alert = {
                    'detected': True,
                    'type': AlertType.DEGRADATION,
                    'previous_r2': round(previous_r2, 4),
                    'latest_r2': round(latest_r2, 4),
                    'degradation_percentage': round(degradation_pct, 2),
                    'threshold': self.performance_threshold,
                    'timestamp': datetime.now().isoformat()
                }

                logger.warning(f"⚠️ 성능 저하 감지: {degradation_pct:.2f}%")
                return alert

            return {'detected': False}

        except Exception as e:
            logger.error(f"❌ 성능 저하 확인 실패: {e}")
            return None

    def get_trend_data(self, weeks: int = 10) -> List[Dict[str, Any]]:
        """재학습 추세 데이터"""
        try:
            if not self.history_file.exists():
                return []

            results = []
            with open(self.history_file, 'r') as f:
                for line in f:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            # 최근 N개만 추출
            recent_results = results[-weeks:]

            # 추세 데이터 생성
            trend_data = []
            for i, result in enumerate(recent_results, 1):
                r2 = result.get('ensemble', {}).get('r2')
                timestamp = result.get('timestamp')

                if r2 is not None:
                    trend_data.append({
                        'week': f"{i}주",
                        'r2': round(r2, 4),
                        'timestamp': timestamp,
                        'status': result.get('status')
                    })

            logger.info(f"✅ 추세 데이터 조회: {len(trend_data)}개")
            return trend_data

        except Exception as e:
            logger.error(f"❌ 추세 데이터 조회 실패: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """재학습 통계"""
        try:
            if not self.history_file.exists():
                return {}

            results = []
            with open(self.history_file, 'r') as f:
                for line in f:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            if not results:
                return {}

            # 성능 메트릭 추출
            r2_scores = []
            successful_count = 0
            failed_count = 0

            for result in results:
                r2 = result.get('ensemble', {}).get('r2')
                if r2 is not None:
                    r2_scores.append(r2)

                status = result.get('status', 'unknown')
                if status == 'success':
                    successful_count += 1
                elif status == 'failed':
                    failed_count += 1

            stats = {
                'total_trainings': len(results),
                'successful_trainings': successful_count,
                'failed_trainings': failed_count,
                'average_r2': round(np.mean(r2_scores), 4) if r2_scores else 0,
                'max_r2': round(np.max(r2_scores), 4) if r2_scores else 0,
                'min_r2': round(np.min(r2_scores), 4) if r2_scores else 0,
                'success_rate': round(
                    (successful_count / len(results)) * 100, 1
                ) if results else 0
            }

            logger.info(f"✅ 통계 계산: {stats['total_trainings']}회, {stats['success_rate']}% 성공")
            return stats

        except Exception as e:
            logger.error(f"❌ 통계 계산 실패: {e}")
            return {}

    def estimate_next_training(self) -> Optional[Dict[str, Any]]:
        """다음 재학습 시간 예측"""
        try:
            if not self.config_file.exists():
                return None

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            schedule = config.get('schedule', {})

            # 현재 시간
            now = datetime.now()

            # 스케줄 분석 (예: 매주 목요일 10:00)
            day_of_week = schedule.get('day_of_week', 'thursday')
            hour = schedule.get('hour', 10)
            minute = schedule.get('minute', 0)

            # 요일 매핑
            days_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2,
                'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
            }

            target_day = days_map.get(day_of_week.lower(), 3)

            # 다음 실행 날짜 계산
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7

            next_training = now + timedelta(days=days_ahead)
            next_training = next_training.replace(hour=hour, minute=minute, second=0)

            result = {
                'scheduled_time': next_training.isoformat(),
                'days_remaining': days_ahead,
                'schedule': {
                    'day': day_of_week,
                    'time': f"{hour:02d}:{minute:02d}"
                }
            }

            logger.info(f"✅ 다음 재학습: {days_ahead}일 후 ({day_of_week} {hour:02d}:{minute:02d})")
            return result

        except Exception as e:
            logger.error(f"❌ 다음 학습 시간 예측 실패: {e}")
            return None

    def get_health_status(self) -> Dict[str, Any]:
        """전체 시스템 상태"""
        latest = self.get_latest_result()
        degradation = self.check_performance_degradation()
        stats = self.get_statistics()
        next_training = self.estimate_next_training()

        # 전체 상태 판단
        status = "healthy"
        if degradation and degradation.get('detected'):
            status = "warning"
        if latest and latest.get('status') == 'failed':
            status = "error"

        result = {
            'status': status,
            'latest_result': latest,
            'degradation': degradation,
            'statistics': stats,
            'next_training': next_training,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"✅ 시스템 상태: {status}")
        return result

    def get_model_comparison(self) -> Optional[Dict[str, Any]]:
        """개별 모델 성능 비교"""
        try:
            latest = self.get_latest_result()
            if not latest:
                return None

            models = latest.get('models', {})
            ensemble = latest.get('ensemble', {})

            comparison = {
                'timestamp': latest.get('timestamp'),
                'individual_models': models,
                'ensemble': ensemble
            }

            # 앙상블 vs 최고 개별 모델
            individual_r2s = [m.get('r2', 0) for m in models.values() if isinstance(m, dict) and 'r2' in m]
            if individual_r2s:
                max_individual_r2 = max(individual_r2s)
                ensemble_r2 = ensemble.get('r2', 0)
                improvement = ((ensemble_r2 - max_individual_r2) / max_individual_r2) * 100 if max_individual_r2 > 0 else 0

                comparison['ensemble_improvement'] = {
                    'max_individual_r2': round(max_individual_r2, 4),
                    'ensemble_r2': round(ensemble_r2, 4),
                    'improvement_percentage': round(improvement, 2)
                }

            return comparison

        except Exception as e:
            logger.error(f"❌ 모델 비교 실패: {e}")
            return None


# 전역 인스턴스
monitor = RetrainingMonitor()
