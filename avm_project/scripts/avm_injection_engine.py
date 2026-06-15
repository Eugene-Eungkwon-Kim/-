"""
AVM Valuation Model 전체 데이터 인젝션 및 학습 스크립트
현재 모든 학습 데이터를 모델에 주입하고 재학습 수행
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error, r2_score
import joblib


class AVMModelInjectionEngine:
    """AVM 모델 데이터 인젝션 및 학습 엔진"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.model_dir = Path(__file__).parent.parent / "models"
        self.output_dir = Path(__file__).parent.parent / "output"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.models = {}
        self.results = {}
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None

    def load_all_training_data(self):
        """모든 학습 데이터 로드"""
        print("\n" + "="*70)
        print("📊 Step 1: 모든 학습 데이터 로드")
        print("="*70)

        # Raw 데이터 확인
        raw_files = list(self.data_dir.glob("raw/*.csv"))
        print(f"\n📁 Raw 데이터 파일 ({len(raw_files)}개):")
        for f in raw_files:
            print(f"   - {f.name}")

        # Processed 데이터 확인
        processed_files = list(self.data_dir.glob("processed/*.csv"))
        print(f"\n📁 Processed 데이터 파일 ({len(processed_files)}개):")
        for f in processed_files:
            print(f"   - {f.name}")

        # 가장 최신의 processed 데이터 로드
        if processed_files:
            latest_file = max(processed_files, key=lambda x: x.stat().st_mtime)
            print(f"\n✅ 최신 processed 데이터 로드: {latest_file.name}")
            df = pd.read_csv(latest_file)
        elif raw_files:
            latest_file = max(raw_files, key=lambda x: x.stat().st_mtime)
            print(f"\n✅ Raw 데이터 로드: {latest_file.name}")
            df = pd.read_csv(latest_file)
        else:
            print("\n⚠️ 학습 데이터를 찾을 수 없습니다")
            # 샘플 데이터 생성
            print("📝 샘플 데이터 생성 중...")
            np.random.seed(42)
            df = pd.DataFrame({
                'area_sqm': np.random.uniform(50, 300, 500),
                'year_built': np.random.randint(1980, 2024, 500),
                'rooms': np.random.randint(1, 6, 500),
                'bathrooms': np.random.randint(1, 4, 500),
                'parking': np.random.randint(0, 3, 500),
                'floor': np.random.randint(1, 30, 500),
                'total_floor': np.random.randint(5, 50, 500),
                'condition': np.random.randint(1, 10, 500),
                'original_price': np.random.uniform(200000, 2000000, 500),
                'appraised_price': np.random.uniform(200000, 2000000, 500),
                'outstanding_debt': np.random.uniform(0, 1000000, 500),
                'market_price': np.random.uniform(200000, 2000000, 500),
                'transaction_count_1y': np.random.randint(0, 50, 500),
                'ltv': np.random.uniform(0.3, 0.9, 500),
                'loan_term_months': np.random.randint(60, 360, 500),
                'days_on_market': np.random.randint(0, 180, 500),
                'appraisal_rounds': np.random.randint(1, 5, 500),
                'age_years': np.random.randint(0, 100, 500),
                'price_per_sqm': np.random.uniform(2000, 20000, 500),
                'debt_to_price_ratio': np.random.uniform(0.3, 0.9, 500),
                'price_variance': np.random.uniform(0, 0.5, 500),
                'market_trend': np.random.uniform(-0.1, 0.1, 500),
                'interest_rate': np.random.uniform(0.03, 0.08, 500)
            })

        print(f"\n📈 데이터 형태: {df.shape}")
        print(f"   - 행(Rows): {df.shape[0]}")
        print(f"   - 열(Columns): {df.shape[1]}")
        print(f"\n📊 데이터 타입:")
        print(df.dtypes)
        print(f"\n📌 샘플 데이터:")
        print(df.head(3))

        return df

    def prepare_features(self, df):
        """특성 준비"""
        print("\n" + "="*70)
        print("🔧 Step 2: 특성 준비 및 전처리")
        print("="*70)

        # 타겟 변수 설정
        target_col = 'market_price'
        if target_col not in df.columns:
            print(f"\n⚠️ 타겟 컬럼 '{target_col}'이 없습니다. 마지막 컬럼을 타겟으로 사용")
            target_col = df.columns[-1]

        # 결측치 처리
        print(f"\n🔍 결측치 확인:")
        missing = df.isnull().sum()
        if missing.sum() > 0:
            print(f"   결측치 발견: {missing[missing > 0]}")
            df = df.fillna(df.mean(numeric_only=True))
            print(f"   ✅ 평균값으로 대체")
        else:
            print(f"   ✅ 결측치 없음")

        # 아웃라이어 제거
        print(f"\n🎯 아웃라이어 감지 및 제거:")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        initial_rows = len(df)

        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            df = df[(df[col] >= lower) & (df[col] <= upper)]

        removed = initial_rows - len(df)
        print(f"   제거된 행: {removed}")
        print(f"   남은 행: {len(df)}")

        # 특성과 타겟 분리 (수치형만)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target_col in numeric_cols:
            numeric_cols.remove(target_col)

        X = df[numeric_cols]
        y = df[target_col]

        print(f"\n✅ 특성 분리 완료 (수치형만):")
        print(f"   제거된 문자열 컬럼: property_id, property_type, region, district, condition")
        print(f"   사용 특성 수: {len(numeric_cols)}")
        print(f"   X 형태: {X.shape}")
        print(f"   y 형태: {y.shape}")

        # 데이터 정규화
        print(f"\n📊 데이터 정규화:")
        X_min = X.min()
        X_max = X.max()
        # 영점 나누기 방지
        X_max = X_max.replace(0, 1)
        X_normalized = (X - X_min) / (X_max - X_min)
        X_normalized = X_normalized.fillna(0)
        print(f"   Min-Max 정규화 적용")

        return X_normalized, y, X.columns.tolist()

    def split_data(self, X, y, test_size=0.2):
        """데이터 분할"""
        print("\n" + "="*70)
        print("✂️ Step 3: 데이터 분할 (Train/Test)")
        print("="*70)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        print(f"\n✅ 데이터 분할 완료:")
        print(f"   Train 데이터: {X_train.shape[0]} 샘플 ({(1-test_size)*100:.0f}%)")
        print(f"   Test 데이터: {X_test.shape[0]} 샘플 ({test_size*100:.0f}%)")

        return X_train, X_test, y_train, y_test

    def train_models(self, X_train, y_train):
        """모든 모델 학습"""
        print("\n" + "="*70)
        print("🤖 Step 4: 모델 학습 (6개 모델)")
        print("="*70)

        models_to_train = {
            'LinearRegression': LinearRegression(),
            'DecisionTreeRegressor': DecisionTreeRegressor(max_depth=10, random_state=42),
            'RandomForestRegressor': RandomForestRegressor(
                n_estimators=100, max_depth=15, random_state=42, n_jobs=-1
            ),
            'GradientBoostingRegressor': GradientBoostingRegressor(
                n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
            ),
            'XGBRegressor': xgb.XGBRegressor(
                n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, n_jobs=-1
            ),
            'LGBMRegressor': lgb.LGBMRegressor(
                n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, n_jobs=-1
            )
        }

        for model_name, model in models_to_train.items():
            print(f"\n🔨 {model_name} 학습 중...")
            model.fit(X_train, y_train)
            self.models[model_name] = model
            print(f"   ✅ 완료")

        return self.models

    def evaluate_models(self, X_train, X_test, y_train, y_test):
        """모델 평가"""
        print("\n" + "="*70)
        print("📊 Step 5: 모델 평가")
        print("="*70)

        for model_name, model in self.models.items():
            print(f"\n🔍 {model_name}:")

            # Train 성능
            y_train_pred = model.predict(X_train)
            train_r2 = r2_score(y_train, y_train_pred)
            train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
            train_mae = mean_absolute_error(y_train, y_train_pred)

            # Test 성능
            y_test_pred = model.predict(X_test)
            test_r2 = r2_score(y_test, y_test_pred)
            test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
            test_mae = mean_absolute_error(y_test, y_test_pred)
            test_mape = mean_absolute_percentage_error(y_test, y_test_pred)

            # 교차 검증
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='r2')

            result = {
                'model_name': model_name,
                'train_r2': float(train_r2),
                'train_rmse': float(train_rmse),
                'train_mae': float(train_mae),
                'test_r2': float(test_r2),
                'test_rmse': float(test_rmse),
                'test_mae': float(test_mae),
                'test_mape': float(test_mape),
                'cv_mean': float(cv_scores.mean()),
                'cv_std': float(cv_scores.std()),
                'cv_scores': cv_scores.tolist()
            }

            self.results[model_name] = result

            print(f"   Train R²:    {train_r2:.4f}")
            print(f"   Test R²:     {test_r2:.4f}")
            print(f"   Test RMSE:   {test_rmse:.2f}")
            print(f"   Test MAE:    {test_mae:.2f}")
            print(f"   Test MAPE:   {test_mape:.4f}")
            print(f"   CV R² (Mean): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        return self.results

    def save_models(self):
        """모델 저장"""
        print("\n" + "="*70)
        print("💾 Step 6: 모델 저장")
        print("="*70)

        for model_name, model in self.models.items():
            model_file = self.model_dir / f"{model_name}_model.joblib"
            joblib.dump(model, model_file)
            print(f"   ✅ {model_name}: {model_file}")

        return self.model_dir

    def generate_report(self, feature_names):
        """종합 보고서 생성"""
        print("\n" + "="*70)
        print("📋 Step 7: 종합 보고서 생성")
        print("="*70)

        # 최고 성능 모델
        best_model = max(self.results.items(), key=lambda x: x[1]['test_r2'])

        report = {
            'timestamp': datetime.now().isoformat(),
            'data_injection_summary': {
                'total_samples': len(self.X_train) + len(self.X_test),
                'train_samples': len(self.X_train),
                'test_samples': len(self.X_test),
                'features': len(feature_names),
                'feature_names': feature_names
            },
            'model_results': self.results,
            'best_model': {
                'name': best_model[0],
                'test_r2': best_model[1]['test_r2'],
                'test_rmse': best_model[1]['test_rmse'],
                'test_mae': best_model[1]['test_mae'],
                'cv_mean': best_model[1]['cv_mean']
            },
            'model_ranking': [
                {'rank': i, 'name': name, 'test_r2': result['test_r2'], 'test_rmse': result['test_rmse']}
                for i, (name, result) in enumerate(
                    sorted(self.results.items(), key=lambda x: x[1]['test_r2'], reverse=True),
                    1
                )
            ]
        }

        # 보고서 저장
        report_file = self.output_dir / f"avm_injection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n✅ 보고서 저장: {report_file}")

        return report, report_file

    def run_injection_pipeline(self):
        """전체 인젝션 파이프라인 실행"""
        print("\n" + "="*80)
        print("🚀 AVM VALUATION MODEL 전체 데이터 인젝션 및 학습 시작")
        print("="*80)

        start_time = datetime.now()

        # Step 1: 데이터 로드
        df = self.load_all_training_data()

        # Step 2: 특성 준비
        X, y, feature_names = self.prepare_features(df)

        # Step 3: 데이터 분할
        self.X_train, self.X_test, self.y_train, self.y_test = self.split_data(X, y)

        # Step 4: 모델 학습
        self.train_models(self.X_train, self.y_train)

        # Step 5: 모델 평가
        self.evaluate_models(self.X_train, self.X_test, self.y_train, self.y_test)

        # Step 6: 모델 저장
        model_dir = self.save_models()

        # Step 7: 보고서 생성
        report, report_file = self.generate_report(feature_names)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 최종 요약
        print("\n" + "="*80)
        print("✅ 데이터 인젝션 및 학습 완료")
        print("="*80)
        print(f"\n⏱️ 소요 시간: {duration:.2f}초")
        print(f"\n📊 최고 성능 모델: {report['best_model']['name']}")
        print(f"   Test R²: {report['best_model']['test_r2']:.4f}")
        print(f"   Test RMSE: {report['best_model']['test_rmse']:.2f}")
        print(f"   CV R²: {report['best_model']['cv_mean']:.4f}")

        print(f"\n📈 모델 순위:")
        for item in report['model_ranking']:
            print(f"   {item['rank']}. {item['name']}: R² = {item['test_r2']:.4f}")

        print(f"\n💾 모델 저장 위치: {model_dir}")
        print(f"📄 보고서 저장 위치: {report_file}")

        return report


if __name__ == "__main__":
    engine = AVMModelInjectionEngine()
    report = engine.run_injection_pipeline()
