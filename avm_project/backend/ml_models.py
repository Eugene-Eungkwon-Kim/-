"""
모델 관리 및 예측 모듈
Phase D-2에서 생성한 모델 파일 로드 및 예측 기능
"""

import joblib
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR = PROJECT_ROOT / "avm_project" / "models"


class ModelManager:
    """모델 관리 및 예측 클래스"""

    MODEL_NAMES = {
        'linear_regression': 'Linear Regression',
        'decision_tree': 'Decision Tree',
        'random_forest': 'Random Forest',
        'gradient_boosting': 'Gradient Boosting',
        'xgboost': 'XGBoost',
        'lightgbm': 'LightGBM',
        'ensemble': 'Ensemble (Meta Learner)'
    }

    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Dict] = {}
        self.latest_version: Dict[str, str] = {}
        self.load_models()

    def load_models(self) -> None:
        """모든 모델 파일 로드"""
        try:
            if not MODEL_DIR.exists():
                logger.warning(f"모델 디렉토리 없음: {MODEL_DIR}")
                self._create_demo_models()
                return

            # 모델 파일 탐색
            model_files = list(MODEL_DIR.glob("*.joblib"))

            if not model_files:
                logger.warning("모델 파일이 없습니다. 데모 모델 생성 중...")
                self._create_demo_models()
                return

            # 모델 이름별로 최신 버전 찾기
            version_map: Dict[str, List[tuple]] = {}

            for model_file in model_files:
                # 파일명: model_xgboost_v20260619_100000.joblib
                # 또는 ensemble_model_v20260619_100000.joblib
                stem = model_file.stem
                parts = stem.split('_')

                # 모델 타입 추출
                model_type = None
                timestamp = None

                if 'ensemble' in stem:
                    model_type = 'ensemble'
                    # ensemble_model_v20260619_100000
                    if len(parts) >= 4:
                        timestamp = parts[-1]
                elif 'model' in stem and len(parts) >= 3:
                    # model_xgboost_v20260619_100000
                    model_type = parts[1]
                    if len(parts) >= 4:
                        timestamp = parts[-1]

                if not model_type or not timestamp:
                    logger.warning(f"파일명 형식 오류: {stem}")
                    continue

                if model_type not in version_map:
                    version_map[model_type] = []

                version_map[model_type].append((timestamp, model_file))

            # 각 모델의 최신 버전 로드
            for model_type, versions in version_map.items():
                versions.sort(reverse=True)
                latest_file = versions[0][1]

                try:
                    model = joblib.load(latest_file)
                    model_id = f"{model_type}_latest"

                    self.models[model_id] = model
                    self.latest_version[model_type] = versions[0][0]

                    self.model_metadata[model_id] = {
                        'type': model_type,
                        'file': latest_file.name,
                        'version': versions[0][0],
                        'loaded_at': datetime.now().isoformat(),
                        'display_name': self.MODEL_NAMES.get(model_type, model_type)
                    }

                    logger.info(f"✅ 모델 로드: {model_id} ({latest_file.name})")

                except Exception as e:
                    logger.error(f"❌ 모델 로드 실패 ({latest_file}): {e}")

            if self.models:
                logger.info(f"✅ 총 {len(self.models)}개 모델 로드 완료")
            else:
                logger.warning("로드된 모델이 없습니다")

        except Exception as e:
            logger.error(f"❌ 모델 로드 중 오류: {e}")

    def _create_demo_models(self) -> None:
        """데모 모델 생성 (테스트용)"""
        try:
            logger.info("데모 모델 생성 중...")

            # 간단한 Mock 모델 생성
            from sklearn.linear_model import LinearRegression
            import numpy as np

            # 더미 데이터로 간단한 모델 학습
            X_dummy = np.random.rand(100, 17)
            y_dummy = np.random.rand(100) * 100000000

            demo_model = LinearRegression()
            demo_model.fit(X_dummy, y_dummy)

            # 메타데이터만 저장 (테스트용)
            model_id = "demo_latest"
            self.models[model_id] = demo_model
            self.model_metadata[model_id] = {
                'type': 'linear_regression',
                'file': 'demo_model.joblib',
                'version': '20260619_000000',
                'loaded_at': datetime.now().isoformat(),
                'display_name': 'Linear Regression (Demo)',
                'is_demo': True
            }

            logger.info("✅ 데모 모델 생성 완료")

        except Exception as e:
            logger.error(f"❌ 데모 모델 생성 실패: {e}")

    def get_model(self, model_id: str) -> Optional[Any]:
        """특정 모델 조회"""
        if model_id not in self.models:
            if model_id == 'latest' and self.models:
                # 가장 최근 모델 반환
                return list(self.models.values())[0]
            self.load_models()
        return self.models.get(model_id)

    def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록"""
        models_list = []

        for model_id, metadata in self.model_metadata.items():
            models_list.append({
                'id': model_id,
                'name': metadata.get('display_name'),
                'type': metadata.get('type'),
                'version': metadata.get('version'),
                'loaded': True,
                'file': metadata.get('file')
            })

        return sorted(models_list, key=lambda x: x['name'])

    def make_prediction(
        self,
        model_id: str,
        features: Dict[str, float],
        ensemble: bool = True
    ) -> Optional[Dict[str, Any]]:
        """예측 수행"""
        try:
            # 모델 선택
            if model_id == 'latest':
                model = list(self.models.values())[0] if self.models else None
                used_model_id = list(self.model_metadata.keys())[0] if self.model_metadata else 'unknown'
            else:
                model = self.get_model(model_id)
                used_model_id = model_id

            if model is None:
                logger.error(f"❌ 모델 없음: {model_id}")
                return None

            # 특성을 리스트로 변환 (정렬된 순서)
            feature_values = list(features.values())
            feature_array = np.array([feature_values])

            # 예측
            prediction = model.predict(feature_array)[0]

            # 신뢰도 (일부 모델에서만 가능)
            confidence = None
            if hasattr(model, 'predict_proba'):
                try:
                    proba = model.predict_proba(feature_array)
                    confidence = float(np.max(proba))
                except:
                    pass

            return {
                'prediction': float(prediction),
                'model_id': used_model_id,
                'timestamp': datetime.now().isoformat(),
                'confidence': confidence,
                'features_count': len(features)
            }

        except Exception as e:
            logger.error(f"❌ 예측 실패 ({model_id}): {e}")
            return None

    def get_model_metadata(self, model_id: str) -> Optional[Dict]:
        """모델 메타데이터"""
        return self.model_metadata.get(model_id)

    def get_all_metadata(self) -> Dict[str, Dict]:
        """모든 모델 메타데이터"""
        return self.model_metadata.copy()

    def reload_models(self) -> int:
        """모델 다시 로드"""
        self.models.clear()
        self.model_metadata.clear()
        self.latest_version.clear()
        self.load_models()
        return len(self.models)

    def get_model_performance(self, model_id: str) -> Optional[Dict]:
        """모델 성능 메트릭 (재학습 이력에서)"""
        try:
            from backend.database import history_manager

            history = history_manager.get_history(limit=10)

            if not history:
                return None

            # 모델 타입별로 성능 찾기
            for result in history:
                models = result.get('models', {})

                # model_id에서 타입 추출
                model_type = model_id.replace('_latest', '').replace('model_', '')

                if model_type in models:
                    return models[model_type]

            return None

        except Exception as e:
            logger.error(f"성능 메트릭 조회 실패: {e}")
            return None


# 전역 인스턴스
model_manager = ModelManager()
