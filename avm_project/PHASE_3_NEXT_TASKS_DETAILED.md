# 📋 Phase 3 다음 작업 상세 보고서

**작성일:** 2026-06-19  
**기간:** 이번 주 (2026-06-19 ~ 2026-06-23)  
**상태:** 상세 계획 수립 완료

---

## 🎯 이번 주 목표 (4가지 작업)

```
┌─────────────────────────────────────────┐
│ Phase 3 Week 1: 데이터 연동 심화        │
├─────────────────────────────────────────┤
│ 1. ml_models.py 작성 (모델 로드)       │
│ 2. retraining_monitor.py 작성 (통합)  │
│ 3. WebSocket 엔드포인트 추가            │
│ 4. 프론트엔드 실시간 업데이트           │
└─────────────────────────────────────────┘
```

---

## 📝 작업 1: backend/ml_models.py 작성

### 개요
```
목적: 저장된 모델 파일 로드 및 예측 기능
크기: 약 300-400줄
의존성: joblib, numpy, pandas
위치: /home/user/-/avm_project/backend/ml_models.py
```

### 상세 구현

#### 1.1 클래스 설계

```python
class ModelManager:
    """모델 관리 및 예측 클래스"""
    
    def __init__(self):
        # 모델 메타데이터
        self.models = {}
        self.model_info = {}
        self.feature_importance = {}
        self.load_models()
    
    def load_models(self) -> None:
        """Phase D-2에서 생성한 모델 파일 로드"""
        # 1. 모델 디렉토리 탐색
        # 2. .joblib 파일 찾기
        # 3. 각 모델 로드
        # 4. 메타데이터 저장
    
    def get_model(self, model_id: str):
        """특정 모델 조회"""
        # 1. 모델 존재 확인
        # 2. 없으면 재로드
        # 3. 반환
    
    def make_prediction(self, model_id: str, features: Dict):
        """예측 수행"""
        # 1. 모델 조회
        # 2. 특성 검증
        # 3. 예측 실행
        # 4. 결과 반환
    
    def get_feature_importance(self, model_id: str):
        """특성 중요도 조회"""
        # 1. 캐시 확인
        # 2. 없으면 계산
        # 3. 반환
    
    def get_model_performance(self, model_id: str):
        """모델 성능 메트릭"""
        # 1. 재학습 이력 로드
        # 2. 최신 성능 추출
        # 3. 반환
```

#### 1.2 구현 코드

```python
# backend/ml_models.py

import joblib
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR = PROJECT_ROOT / "avm_project" / "models"
LOGS_DIR = PROJECT_ROOT / "avm_project" / "logs"


class ModelManager:
    """모델 관리 및 예측"""
    
    MODEL_NAMES = {
        'linear_regression': 'Linear Regression',
        'decision_tree': 'Decision Tree',
        'random_forest': 'Random Forest',
        'gradient_boosting': 'Gradient Boosting',
        'xgboost': 'XGBoost',
        'lightgbm': 'LightGBM',
        'ensemble': 'Ensemble'
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
                return
            
            # 모델 파일 탐색
            model_files = list(MODEL_DIR.glob("*.joblib"))
            
            if not model_files:
                logger.warning("모델 파일이 없습니다. Phase D-2를 실행하세요.")
                return
            
            # 모델 이름별로 최신 버전 찾기
            version_map: Dict[str, List[tuple]] = {}
            
            for model_file in model_files:
                # 파일명: model_xgboost_v20260619_100000.joblib
                parts = model_file.stem.split('_')
                
                if len(parts) < 3:
                    continue
                
                model_type = parts[1]
                timestamp = parts[3] if len(parts) > 3 else "unknown"
                
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
                    
                    logger.info(f"모델 로드: {model_id} ({latest_file.name})")
                
                except Exception as e:
                    logger.error(f"모델 로드 실패 ({latest_file}): {e}")
            
            if self.models:
                logger.info(f"총 {len(self.models)}개 모델 로드 완료")
            
        except Exception as e:
            logger.error(f"모델 로드 중 오류: {e}")
    
    def get_model(self, model_id: str) -> Optional[Any]:
        """특정 모델 조회"""
        if model_id not in self.models:
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
                'loaded': True
            })
        
        return models_list
    
    def make_prediction(
        self,
        model_id: str,
        features: Dict[str, float],
        ensemble: bool = True
    ) -> Optional[Dict[str, Any]]:
        """예측 수행"""
        try:
            model = self.get_model(model_id)
            
            if model is None:
                logger.error(f"모델 없음: {model_id}")
                return None
            
            # 특성을 리스트로 변환
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
                'model_id': model_id,
                'timestamp': datetime.now().isoformat(),
                'confidence': confidence,
                'features_count': len(features)
            }
        
        except Exception as e:
            logger.error(f"예측 실패 ({model_id}): {e}")
            return None
    
    def get_model_metadata(self, model_id: str) -> Optional[Dict]:
        """모델 메타데이터"""
        return self.model_metadata.get(model_id)
    
    def reload_models(self) -> int:
        """모델 다시 로드"""
        self.models.clear()
        self.model_metadata.clear()
        self.load_models()
        return len(self.models)


# 전역 인스턴스
model_manager = ModelManager()
```

#### 1.3 API 엔드포인트 추가

```python
# backend/main.py에 추가

from backend.ml_models import model_manager
from backend.models import PredictionInput, PredictionOutput

@app.get("/models/available", tags=["Models"])
async def get_available_models(token: str = Depends(verify_token)):
    """사용 가능한 모델 목록"""
    models = model_manager.get_available_models()
    return {
        "data": models,
        "total": len(models)
    }


@app.post("/predictions", tags=["Predictions"])
async def create_prediction(
    request: PredictionInput,
    token: str = Depends(verify_token)
):
    """예측 생성"""
    model_id = request.model_id or "ensemble_latest"
    
    result = model_manager.make_prediction(
        model_id=model_id,
        features=request.features
    )
    
    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Prediction failed"
        )
    
    return result


@app.post("/models/reload", tags=["Admin"])
async def reload_models(token: str = Depends(verify_token)):
    """모델 재로드"""
    count = model_manager.reload_models()
    return {
        "status": "reloaded",
        "models_loaded": count
    }
```

### 체크리스트

```
[ ] 1.1 기본 클래스 구조 작성
[ ] 1.2 load_models() 메서드 완성
[ ] 1.3 make_prediction() 메서드 완성
[ ] 1.4 메타데이터 관리 기능
[ ] 1.5 API 엔드포인트 추가
[ ] 1.6 에러 핸들링
[ ] 1.7 로깅 추가
[ ] 1.8 테스트 (mock 모델로)
```

---

## 📝 작업 2: backend/retraining_monitor.py 작성

### 개요
```
목적: Phase D-2 재학습 결과 실시간 모니터링
크기: 약 250-350줄
의존성: json, pathlib, datetime, logging
위치: /home/user/-/avm_project/backend/retraining_monitor.py
```

### 상세 구현

#### 2.1 클래스 설계

```python
class RetrainingMonitor:
    """재학습 모니터 클래스"""
    
    def __init__(self):
        self.history_file = Path(...)  # retrain_history.jsonl
        self.cache = {}
        self.last_read = None
    
    def get_latest_result(self) -> Optional[Dict]:
        """최신 재학습 결과"""
        # Phase D-2가 쓴 JSONL 파일 읽기
        # 마지막 줄 파싱
        # 캐시 업데이트
        # 반환
    
    def check_performance_degradation(self) -> Optional[Dict]:
        """성능 저하 감지"""
        # 최신 결과와 이전 결과 비교
        # 5% 이상 저하시 경고
    
    def get_trend_data(self, weeks: int = 10) -> List[Dict]:
        """추세 데이터"""
        # 재학습 이력에서 R² 추세 추출
        # 시간순 정렬
        # 반환
    
    def estimate_next_training(self) -> Optional[datetime]:
        """다음 재학습 시간 예측"""
        # config.json에서 스케줄 읽기
        # 다음 실행 시간 계산
    
    def send_alert(self, alert_type: str, message: str):
        """알림 전송"""
        # 이메일 또는 Slack 알림
```

#### 2.2 구현 코드

```python
# backend/retraining_monitor.py

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
AVM_PROJECT = PROJECT_ROOT / "avm_project"
HISTORY_FILE = AVM_PROJECT / "logs" / "retrain_history.jsonl"
CONFIG_FILE = AVM_PROJECT / "config" / "schedule_config.json"


class AlertType(str, Enum):
    """알림 타입"""
    DEGRADATION = "degradation"  # 성능 저하
    FAILURE = "failure"           # 학습 실패
    SUCCESS = "success"           # 학습 성공
    THRESHOLD = "threshold"       # 임계값 초과


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
                    logger.info(f"성능 임계값: {self.performance_threshold}")
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
    
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
            
            logger.info(f"최신 결과 로드: {latest_result.get('timestamp')}")
            return latest_result
        
        except Exception as e:
            logger.error(f"최신 결과 로드 실패: {e}")
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
            logger.error(f"이전 결과 로드 실패: {e}")
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
                
                return {
                    'detected': True,
                    'type': AlertType.DEGRADATION,
                    'previous_r2': round(previous_r2, 4),
                    'latest_r2': round(latest_r2, 4),
                    'degradation_percentage': round(degradation_pct, 2),
                    'threshold': self.performance_threshold,
                    'timestamp': datetime.now().isoformat()
                }
            
            return {'detected': False}
        
        except Exception as e:
            logger.error(f"성능 저하 확인 실패: {e}")
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
            
            return trend_data
        
        except Exception as e:
            logger.error(f"추세 데이터 조회 실패: {e}")
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
            
            import numpy as np
            
            return {
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
        
        except Exception as e:
            logger.error(f"통계 계산 실패: {e}")
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
            
            target_day = days_map.get(day_of_week.lower(), 3)  # 기본값: 목요일
            
            # 다음 실행 날짜 계산
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:  # 이미 지났으면
                days_ahead += 7
            
            next_training = now + timedelta(days=days_ahead)
            next_training = next_training.replace(hour=hour, minute=minute, second=0)
            
            return {
                'scheduled_time': next_training.isoformat(),
                'days_remaining': days_ahead,
                'schedule': {
                    'day': day_of_week,
                    'time': f"{hour:02d}:{minute:02d}"
                }
            }
        
        except Exception as e:
            logger.error(f"다음 학습 시간 예측 실패: {e}")
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """전체 상태"""
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
        
        return {
            'status': status,
            'latest_result': latest,
            'degradation': degradation,
            'statistics': stats,
            'next_training': next_training,
            'timestamp': datetime.now().isoformat()
        }


# 전역 인스턴스
monitor = RetrainingMonitor()
```

#### 2.3 API 엔드포인트 추가

```python
# backend/main.py에 추가

from backend.retraining_monitor import monitor

@app.get("/monitoring/retraining", tags=["Monitoring"])
async def get_retraining_status(token: str = Depends(verify_token)):
    """재학습 상태 조회"""
    latest = monitor.get_latest_result()
    next_training = monitor.estimate_next_training()
    
    return {
        'latest': latest,
        'next_training': next_training,
        'timestamp': datetime.now().isoformat()
    }


@app.get("/monitoring/health", tags=["Monitoring"])
async def get_health_status(token: str = Depends(verify_token)):
    """전체 시스템 상태"""
    return monitor.get_health_status()


@app.get("/monitoring/degradation", tags=["Monitoring"])
async def check_degradation(token: str = Depends(verify_token)):
    """성능 저하 확인"""
    degradation = monitor.check_performance_degradation()
    
    if degradation is None:
        return {"status": "no_data"}
    
    return degradation


@app.get("/monitoring/statistics", tags=["Monitoring"])
async def get_statistics(token: str = Depends(verify_token)):
    """재학습 통계"""
    return monitor.get_statistics()
```

### 체크리스트

```
[ ] 2.1 기본 클래스 구조
[ ] 2.2 get_latest_result() 메서드
[ ] 2.3 check_performance_degradation() 메서드
[ ] 2.4 get_trend_data() 메서드
[ ] 2.5 get_statistics() 메서드
[ ] 2.6 estimate_next_training() 메서드
[ ] 2.7 API 엔드포인트 추가
[ ] 2.8 에러 핸들링
[ ] 2.9 로깅
[ ] 2.10 테스트 (mock JSONL 파일로)
```

---

## 📝 작업 3: WebSocket 엔드포인트 추가

### 개요
```
목적: 실시간 데이터 업데이트 (양방향 통신)
크기: 약 200-250줄
기술: WebSocket, asyncio
위치: backend/main.py에 추가
```

### 상세 구현

#### 3.1 WebSocket 구조

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)


# 메시지 유형
class MessageType(str, Enum):
    DASHBOARD_UPDATE = "dashboard_update"
    MODEL_UPDATE = "model_update"
    ALERT = "alert"
    STATUS = "status"
    PING = "ping"
    PONG = "pong"
```

#### 3.2 구현 코드

```python
# backend/main.py의 WebSocket 부분

from fastapi import WebSocket, WebSocketDisconnect
from typing import List
from enum import Enum
import asyncio
import json

class MessageType(str, Enum):
    DASHBOARD_UPDATE = "dashboard_update"
    MODEL_PERFORMANCE = "model_performance"
    ALERT = "alert"
    TRAINING_STATUS = "training_status"
    PING = "ping"
    PONG = "pong"


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str = "all"):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        self.subscriptions[channel].append(websocket)
        
        logger.info(f"WebSocket 연결됨: {len(self.active_connections)}명")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 모든 채널에서 제거
        for channel in self.subscriptions.values():
            if websocket in channel:
                channel.remove(websocket)
        
        logger.info(f"WebSocket 연결 해제: {len(self.active_connections)}명")
    
    async def broadcast(self, message: dict, channel: str = "all"):
        """채널에 브로드캐스트"""
        connections = self.subscriptions.get(channel, [])
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"메시지 전송 실패: {e}")
                self.disconnect(connection)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """개인 메시지"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"개인 메시지 전송 실패: {e}")


manager = ConnectionManager()


# 백그라운드 작업: 주기적 업데이트
async def broadcast_updates():
    """주기적 업데이트 전송 (30초마다)"""
    while True:
        try:
            await asyncio.sleep(30)
            
            # 대시보드 메트릭
            from backend.database import db_manager
            from backend.retraining_monitor import monitor
            
            metrics = {
                'type': MessageType.DASHBOARD_UPDATE,
                'data': {
                    'data_quality': db_manager.get_data_quality_metrics(),
                    'health': monitor.get_health_status()
                },
                'timestamp': datetime.now().isoformat()
            }
            
            await manager.broadcast(metrics, channel="dashboard")
        
        except Exception as e:
            logger.error(f"브로드캐스트 오류: {e}")


# WebSocket 엔드포인트
@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """대시보드 실시간 업데이트"""
    await manager.connect(websocket, channel="dashboard")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 클라이언트 요청 처리
            msg_type = message.get('type')
            
            if msg_type == MessageType.PING:
                await manager.send_personal(
                    websocket,
                    {
                        'type': MessageType.PONG,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            elif msg_type == 'request_update':
                # 즉시 업데이트 요청
                from backend.database import db_manager
                
                update = {
                    'type': MessageType.DASHBOARD_UPDATE,
                    'data': db_manager.get_data_quality_metrics(),
                    'timestamp': datetime.now().isoformat()
                }
                
                await manager.send_personal(websocket, update)
            
            elif msg_type == 'subscribe':
                # 채널 구독
                channel = message.get('channel', 'all')
                await manager.connect(websocket, channel=channel)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket 연결 해제")
    
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """모니터링 실시간 업데이트"""
    await manager.connect(websocket, channel="monitoring")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'request_status':
                # 현재 상태 요청
                from backend.retraining_monitor import monitor
                
                status = {
                    'type': MessageType.TRAINING_STATUS,
                    'data': monitor.get_health_status(),
                    'timestamp': datetime.now().isoformat()
                }
                
                await manager.send_personal(websocket, status)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket 모니터링 오류: {e}")
        manager.disconnect(websocket)


# 앱 시작 시 백그라운드 작업 시작
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 백그라운드 작업 실행"""
    asyncio.create_task(broadcast_updates())
    logger.info("백그라운드 브로드캐스트 시작")
```

### 체크리스트

```
[ ] 3.1 ConnectionManager 클래스
[ ] 3.2 WebSocket 엔드포인트 1 (/ws/dashboard)
[ ] 3.3 WebSocket 엔드포인트 2 (/ws/monitoring)
[ ] 3.4 메시지 유형 정의
[ ] 3.5 브로드캐스트 로직
[ ] 3.6 백그라운드 업데이트 작업
[ ] 3.7 연결 관리 (connect/disconnect)
[ ] 3.8 에러 처리
[ ] 3.9 테스트
```

---

## 📝 작업 4: 프론트엔드 실시간 업데이트

### 개요
```
목적: WebSocket으로 실시간 데이터 수신 및 표시
크기: 약 300-400줄
위치: frontend/hooks/ + frontend/components/
```

### 상세 구현

#### 4.1 WebSocket Hook

```typescript
// frontend/hooks/useWebSocket.ts

'use client'

import { useEffect, useState, useCallback, useRef } from 'react'

interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

export function useWebSocket(
  url: string,
  options: {
    autoConnect?: boolean
    reconnectInterval?: number
    maxReconnectAttempts?: number
  } = {}
) {
  const [data, setData] = useState<any>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ws = useRef<WebSocket | null>(null)
  const reconnectCount = useRef(0)
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null)

  const {
    autoConnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  const connect = useCallback(() => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}${url}`

      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        setConnected(true)
        setError(null)
        reconnectCount.current = 0
        console.log('WebSocket connected:', wsUrl)
      }

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setData(message)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.current.onerror = (event) => {
        setError('WebSocket error occurred')
        console.error('WebSocket error:', event)
      }

      ws.current.onclose = () => {
        setConnected(false)
        console.log('WebSocket disconnected')

        // 자동 재연결
        if (reconnectCount.current < maxReconnectAttempts) {
          reconnectTimer.current = setTimeout(() => {
            console.log(`Reconnecting... (${reconnectCount.current + 1}/${maxReconnectAttempts})`)
            reconnectCount.current++
            connect()
          }, reconnectInterval)
        }
      }
    } catch (e) {
      setError('Failed to connect WebSocket')
      console.error('WebSocket connection error:', e)
    }
  }, [url, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
    }
    if (ws.current) {
      ws.current.close()
    }
  }, [])

  const send = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    data,
    connected,
    error,
    send,
    connect,
    disconnect,
  }
}
```

#### 4.2 대시보드 컴포넌트 업데이트

```typescript
// frontend/components/pages/Dashboard.tsx - 수정 부분

'use client'

import React, { useState, useEffect } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [liveData, setLiveData] = useState<any>(null)

  // WebSocket 연결
  const { data: wsData, connected } = useWebSocket('/ws/dashboard', {
    autoConnect: true,
    reconnectInterval: 5000,
  })

  // WebSocket 데이터 수신
  useEffect(() => {
    if (wsData && wsData.type === 'dashboard_update') {
      setLiveData(wsData.data)
      console.log('Real-time update:', wsData.data)
    }
  }, [wsData])

  // 초기 데이터 로드
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const response = await fetch('http://localhost:8000/dashboard/summary')
        const result = await response.json()
        setData(result)
      } catch (error) {
        console.error('Failed to fetch initial data:', error)
      }
    }

    fetchInitialData()
  }, [])

  // WebSocket 상태 표시
  const connectionStatus = connected ? (
    <span className="inline-flex items-center gap-2 text-success-500">
      <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse"></div>
      실시간 연결됨
    </span>
  ) : (
    <span className="inline-flex items-center gap-2 text-warning-500">
      <div className="w-2 h-2 bg-warning-500 rounded-full animate-pulse"></div>
      연결 중...
    </span>
  )

  return (
    <div className="p-6 space-y-6">
      {/* 연결 상태 표시 */}
      <div className="flex justify-between items-center">
        <h1 className="text-h2 text-neutral-900 font-semibold">대시보드</h1>
        <div className="text-body-sm">{connectionStatus}</div>
      </div>

      {/* 실시간 데이터 표시 */}
      {liveData && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-body-sm text-blue-700">
            <strong>실시간 업데이트:</strong> {liveData.timestamp}
          </p>
        </div>
      )}

      {/* 나머지 대시보드 내용 */}
      {/* ... 기존 코드 ... */}
    </div>
  )
}
```

#### 4.3 실시간 모니터링 페이지

```typescript
// frontend/components/pages/RealtimeMonitoring.tsx

'use client'

import React from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { AlertCircle, CheckCircle, TrendingUp } from 'lucide-react'

export default function RealtimeMonitoring() {
  const { data: wsData, connected } = useWebSocket('/ws/monitoring')

  const healthData = wsData?.data

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-h2 text-neutral-900 font-semibold">실시간 모니터링</h1>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
          connected ? 'bg-success-100 text-success-700' : 'bg-warning-100 text-warning-700'
        }`}>
          {connected ? '● 실시간 연결' : '● 재연결 중'}
        </div>
      </div>

      {/* 시스템 상태 */}
      {healthData && (
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">시스템 상태</h2>
          
          <div className="flex items-center gap-4 mb-4">
            {healthData.status === 'healthy' ? (
              <>
                <CheckCircle className="w-8 h-8 text-success-500" />
                <div>
                  <p className="text-body font-semibold text-success-700">정상</p>
                  <p className="text-body-sm text-neutral-600">모든 지표가 정상입니다</p>
                </div>
              </>
            ) : (
              <>
                <AlertCircle className="w-8 h-8 text-warning-500" />
                <div>
                  <p className="text-body font-semibold text-warning-700">주의</p>
                  <p className="text-body-sm text-neutral-600">확인이 필요합니다</p>
                </div>
              </>
            )}
          </div>

          {/* 성능 저하 알림 */}
          {healthData.degradation?.detected && (
            <div className="mt-4 p-4 bg-warning-50 border border-warning-200 rounded-lg">
              <p className="text-body-sm text-warning-900">
                <strong>성능 저하 감지</strong>
              </p>
              <p className="text-body-sm text-warning-700 mt-1">
                R²: {healthData.degradation.previous_r2.toFixed(4)} → {healthData.degradation.latest_r2.toFixed(4)}
                ({healthData.degradation.degradation_percentage.toFixed(1)}% ↓)
              </p>
            </div>
          )}

          {/* 다음 재학습 */}
          {healthData.next_training && (
            <div className="mt-4 p-4 bg-info-50 border border-info-200 rounded-lg flex items-start gap-3">
              <TrendingUp className="w-5 h-5 text-info-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-body-sm text-info-900 font-medium">다음 재학습</p>
                <p className="text-body-sm text-info-700">
                  {new Date(healthData.next_training.scheduled_time).toLocaleString('ko-KR')}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 통계 */}
      {healthData?.statistics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border border-neutral-300 p-4">
            <p className="text-body-sm text-neutral-600">총 재학습</p>
            <p className="text-h3 font-bold text-neutral-900 mt-1">
              {healthData.statistics.total_trainings}
            </p>
          </div>
          <div className="bg-white rounded-lg border border-neutral-300 p-4">
            <p className="text-body-sm text-neutral-600">성공률</p>
            <p className="text-h3 font-bold text-success-500 mt-1">
              {healthData.statistics.success_rate}%
            </p>
          </div>
          <div className="bg-white rounded-lg border border-neutral-300 p-4">
            <p className="text-body-sm text-neutral-600">평균 R²</p>
            <p className="text-h3 font-bold text-primary-500 mt-1">
              {healthData.statistics.average_r2.toFixed(4)}
            </p>
          </div>
          <div className="bg-white rounded-lg border border-neutral-300 p-4">
            <p className="text-body-sm text-neutral-600">최고 R²</p>
            <p className="text-h3 font-bold text-primary-500 mt-1">
              {healthData.statistics.max_r2.toFixed(4)}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
```

### 체크리스트

```
[ ] 4.1 useWebSocket Hook 작성
[ ] 4.2 MessageType 인터페이스
[ ] 4.3 자동 재연결 로직
[ ] 4.4 Dashboard 컴포넌트 업데이트
[ ] 4.5 RealtimeMonitoring 페이지
[ ] 4.6 WebSocket 상태 표시
[ ] 4.7 실시간 차트 업데이트 (예정)
[ ] 4.8 에러 처리 및 피드백
[ ] 4.9 테스트
```

---

## 📊 전체 작업 요약

| 작업 | 파일 | 크기 | 완료도 | 의존성 |
|------|------|------|--------|--------|
| 1. ml_models.py | backend/ | 350줄 | 0% | joblib, numpy |
| 2. retraining_monitor.py | backend/ | 350줄 | 0% | json, pathlib |
| 3. WebSocket | backend/ | 250줄 | 0% | FastAPI |
| 4. Frontend Hook | frontend/ | 200줄 | 0% | React |
| 4. Frontend Components | frontend/ | 200줄 | 0% | React |
| **총계** | **5개** | **1,350줄** | **0%** | **5개** |

---

## 🎯 완료 조건

```
✅ 작업 1 완료 조건:
   - ml_models.py 파일 생성
   - 모든 6개 모델 자동 로드
   - API 엔드포인트 작동
   - 예측 결과 반환

✅ 작업 2 완료 조건:
   - retraining_monitor.py 파일 생성
   - Phase D-2 JSONL 파일 파싱
   - 성능 저하 감지
   - 모니터링 API 작동

✅ 작업 3 완료 조건:
   - WebSocket 엔드포인트 2개
   - 브로드캐스트 로직
   - 자동 재연결
   - 백그라운드 업데이트

✅ 작업 4 완료 조건:
   - WebSocket Hook 작동
   - 실시간 데이터 수신
   - UI 업데이트 반영
   - 연결 상태 표시
```

---

## 📈 기대 효과

```
작업 완료 시:
✅ Phase D-2 + Phase 2 완전 통합
✅ 실시간 대시보드 업데이트
✅ 자동 성능 모니터링
✅ 즉시 경고 알림
✅ 배포 준비 완료

성능:
- WebSocket 통신: ~100ms 지연
- 업데이트 주기: 30초마다
- 동시 연결: 50+ 사용자 가능
```

---

## ✅ 예상 일정

```
2026-06-19 (오늘)
└─ Phase 3 계획 수립 ✅

2026-06-20 (내일)
└─ 작업 1: ml_models.py 작성

2026-06-21
└─ 작업 2: retraining_monitor.py 작성

2026-06-22
└─ 작업 3: WebSocket 엔드포인트 구현

2026-06-23
└─ 작업 4: 프론트엔드 실시간 업데이트
└─ 통합 테스트

결과: 이번 주 완료 → Phase 3 Week 1 목표 달성
```

---

**상태:** ✅ 상세 계획 완료  
**다음:** 구현 시작  
**브랜치:** claude/eloquent-meitner-lqxu9r
