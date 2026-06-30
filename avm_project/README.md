# AVM (Automated Valuation Model) 프로젝트

NPL(Non-Performing Loans) 데이터 기반 자동감정가 모델 개발 및 실제 평가 시스템 구현

---

## 🤖 **[ Claude 에이전트 주목! ]**

이 프로젝트에서 작업하는 모든 Claude 에이전트는 **반드시** 다음을 읽으세요:

### **✅ 5분 시작 가이드**
```
1. 프로젝트 루트의 AGENT_GUIDE.md 읽기
2. Windows: .\.claude\fix_external_drive.ps1 -AutoFix 실행
3. .claude/AGENT_STARTUP_CHECKLIST.md 완료
4. 작업 시작!
```

### **📚 필수 문서 (순서대로)**
1. **AGENT_GUIDE.md** ← 가장 먼저 읽기!
2. **.claude/AGENT_STARTUP_CHECKLIST.md**
3. **.claude/ENVIRONMENT_SETUP_GUIDE.md**
4. **.claude/EXECUTION_POLICY.md**

### **⚠️ Windows 사용자 (즉시 실행)**
```powershell
.\.claude\fix_external_drive.ps1 -AutoFix
```

### **✨ 준비 완료 신호**
```
✅ 드라이브 설정 완료
✅ Git 상태 정상 (git status)
✅ 필수 문서 읽음
✅ 작업 시작 가능!
```

---

## 프로젝트 개요

이 프로젝트는 역사적 부동산 평가 데이터를 활용하여 머신러닝 기반 자동감정가(AVM) 모델을 개발하고, 이를 실제 평가 시스템에 통합하는 것을 목표로 합니다.

## 디렉토리 구조

```
avm_project/
├── data/                      # 데이터 저장소
│   ├── raw/                   # 원본 데이터
│   └── processed/             # 전처리된 데이터
├── models/                    # 학습된 모델 파일
├── notebooks/                 # Jupyter 노트북 및 분석
├── scripts/                   # Python 스크립트
│   ├── data_preprocessing.py  # 데이터 전처리
│   └── model_development.py   # 모델 개발 및 학습
├── config/                    # 설정 파일
│   └── avm_config.json       # 프로젝트 설정
├── output/                    # 결과 파일
├── docs/                      # 프로젝트 문서
│   └── WBS_프로젝트계획.md    # 프로젝트 계획 및 WBS
├── tests/                     # 테스트 코드
├── requirements.txt           # Python 의존성
└── README.md                  # 이 파일
```

## 시작하기

### 필수 요구사항
- Python 3.9 이상
- Git
- 외장하드 (LG External Drive) - 대용량 데이터 저장용

### 설치

1. **저장소 클론**
```bash
git clone <repository-url>
cd avm_project
```

2. **가상환경 생성**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

3. **의존성 설치**
```bash
pip install -r requirements.txt
```

### 초기 설정

1. **데이터 준비**
   - `D:\NPL폴더`의 데이터를 `data/raw/` 디렉토리에 복사
   - 또는 외장하드에서 데이터를 참조

2. **설정 파일 수정**
   - `config/avm_config.json`에서 프로젝트 설정 확인 및 수정

## 프로젝트 단계

### Phase 1: 데이터 준비 및 분석 (1-2주)
- 데이터 수집 및 검증
- 탐색적 데이터 분석 (EDA)
- 데이터 전처리

**주요 파일:**
- `scripts/data_preprocessing.py` - 데이터 전처리 스크립트
- `notebooks/01_EDA.ipynb` - 탐색적 분석 노트북

### Phase 2: 모델 개발 (2-3주)
- 베이스라인 모델 개발 (선형회귀, 의사결정트리, 랜덤포레스트)
- 고급 모델 개발 (XGBoost, 신경망)
- 하이퍼파라미터 튜닝

**주요 파일:**
- `scripts/model_development.py` - 모델 개발 스크립트
- `notebooks/02_Model_Development.ipynb` - 모델 개발 노트북

### Phase 3: 모델 검증 및 평가 (1-2주)
- 성능 평가 (RMSE, MAE, R²)
- Feature Importance 분석
- SHAP 값을 통한 모델 해석

**주요 파일:**
- `notebooks/03_Model_Evaluation.ipynb` - 모델 평가 노트북
- `output/evaluation_report.md` - 평가 보고서

### Phase 4: 시스템 통합 (2-3주)
- REST API 개발
- 실제 데이터 적용
- 배포 및 운영 설정

### Phase 5: 문서화 및 최종 보고 (1주)
- 기술 문서 작성
- 최종 프로젝트 보고서 작성

## 주요 기술 스택

- **Data Processing:** Pandas, NumPy
- **Visualization:** Matplotlib, Seaborn, Plotly
- **Machine Learning:** Scikit-learn, XGBoost, LightGBM, TensorFlow/Keras
- **Model Interpretation:** SHAP, Lime
- **Web Framework:** FastAPI
- **Database:** SQLite/PostgreSQL
- **Version Control:** Git

## 성공 기준

1. **데이터 정확도:** 전처리된 데이터 품질 지수 > 95%
2. **모델 성능:** R² > 0.85 (테스트 세트)
3. **예측 오차:** RMSE < 설정된 임계값
4. **시스템 안정성:** 99% 이상의 가용성
5. **문서화:** 모든 코드 및 절차 문서화 완료

## 사용 방법

### 데이터 전처리
```bash
python scripts/data_preprocessing.py
```

### 모델 학습
```bash
python scripts/model_development.py
```

### Jupyter 노트북 실행
```bash
jupyter notebook notebooks/
```

### 테스트 실행
```bash
pytest tests/
```

## 폴더 구조 설정

### 로컬 워킹 디렉토리
```
/home/user/-/avm_project/
└── (위 디렉토리 구조 참조)
```

### 외장하드 (LG External Drive)
```
LG_External_Drive:/AVM_Working/
├── data_raw/          # NPL 원본 데이터
├── data_processed/    # 전처리된 데이터
├── models/            # 학습된 모델 (큰 파일)
├── results/           # 분석 결과
└── backup/            # 백업 파일
```

## 주의사항

- 대용량 데이터는 외장하드에 저장하세요
- 정기적으로 백업을 수행하세요
- 모든 변경사항을 Git에 커밋하세요
- 보안이 필요한 데이터는 .gitignore에 포함시키세요

## 문제 해결

### 메모리 부족
- 데이터를 청크 단위로 처리
- 외장하드의 데이터 참조 경로 사용

### 패키지 설치 오류
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### GPU 사용
TensorFlow GPU 설정:
```bash
pip install tensorflow-gpu
# CUDA 및 cuDNN 설치 필요
```

## 문서

자세한 프로젝트 계획과 WBS는 다음 문서를 참조하세요:
- `docs/WBS_프로젝트계획.md` - 프로젝트 전체 계획 및 일정

## 기여

이 프로젝트에 기여하려면:
1. 새로운 브랜치 생성
2. 변경사항 커밋
3. Pull Request 제출

## 라이선스

프로젝트별 라이선스 정의 필요

## 문의

질문이나 제안사항은 이슈를 통해 등록해주세요.

---

**마지막 업데이트:** 2026-06-09
**프로젝트 상태:** 초기화 단계
