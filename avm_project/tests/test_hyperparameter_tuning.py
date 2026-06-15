"""
Unit tests for hyperparameter tuning and model training
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor


class TestModelTraining:
    """Test model training functionality"""

    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data"""
        np.random.seed(42)
        X = np.random.randn(100, 10)
        y = np.random.randn(100)
        return X, y

    def test_linear_regression_training(self, sample_training_data):
        """Test Linear Regression model training"""
        X, y = sample_training_data
        model = LinearRegression()
        model.fit(X, y)

        assert model.coef_ is not None
        assert len(model.coef_) == 10
        assert hasattr(model, 'intercept_')

    def test_decision_tree_training(self, sample_training_data):
        """Test Decision Tree model training"""
        X, y = sample_training_data
        model = DecisionTreeRegressor(random_state=42, max_depth=5)
        model.fit(X, y)

        predictions = model.predict(X)
        assert predictions.shape == y.shape

    def test_random_forest_training(self, sample_training_data):
        """Test Random Forest model training"""
        X, y = sample_training_data
        model = RandomForestRegressor(n_estimators=10, random_state=42, max_depth=5)
        model.fit(X, y)

        predictions = model.predict(X)
        assert predictions.shape == y.shape
        assert len(model.estimators_) == 10

    def test_gradient_boosting_training(self, sample_training_data):
        """Test Gradient Boosting model training"""
        X, y = sample_training_data
        model = GradientBoostingRegressor(n_estimators=10, random_state=42, max_depth=3)
        model.fit(X, y)

        predictions = model.predict(X)
        assert predictions.shape == y.shape

    def test_model_score(self, sample_training_data):
        """Test model scoring"""
        X, y = sample_training_data
        model = LinearRegression()
        model.fit(X, y)

        score = model.score(X, y)
        assert isinstance(score, float)
        assert -1 <= score <= 1


class TestCrossValidation:
    """Test cross-validation functionality"""

    @pytest.fixture
    def cv_data(self):
        """Create data for cross-validation tests"""
        np.random.seed(42)
        X = np.random.randn(50, 8)
        y = X[:, 0] + 0.5 * X[:, 1] + np.random.randn(50) * 0.1
        return X, y

    def test_cv_linear_regression(self, cv_data):
        """Test 5-fold cross-validation for Linear Regression"""
        X, y = cv_data
        model = LinearRegression()
        scores = cross_val_score(model, X, y, cv=5, scoring='r2')

        assert len(scores) == 5
        assert all(-1 <= s <= 1 for s in scores)
        assert scores.mean() > -1

    def test_cv_decision_tree(self, cv_data):
        """Test 5-fold cross-validation for Decision Tree"""
        X, y = cv_data
        model = DecisionTreeRegressor(random_state=42, max_depth=3)
        scores = cross_val_score(model, X, y, cv=5, scoring='r2')

        assert len(scores) == 5
        assert all(isinstance(s, (int, float)) for s in scores)

    def test_cv_random_forest(self, cv_data):
        """Test 5-fold cross-validation for Random Forest"""
        X, y = cv_data
        model = RandomForestRegressor(n_estimators=5, random_state=42, max_depth=3)
        scores = cross_val_score(model, X, y, cv=5, scoring='r2')

        assert len(scores) == 5
        assert scores.std() >= 0

    def test_cv_gradient_boosting(self, cv_data):
        """Test 5-fold cross-validation for Gradient Boosting"""
        X, y = cv_data
        model = GradientBoostingRegressor(n_estimators=5, random_state=42, max_depth=2)
        scores = cross_val_score(model, X, y, cv=5, scoring='r2')

        assert len(scores) == 5

    def test_cv_mean_and_std(self, cv_data):
        """Test cross-validation mean and standard deviation"""
        X, y = cv_data
        model = LinearRegression()
        scores = cross_val_score(model, X, y, cv=5, scoring='r2')

        mean_score = scores.mean()
        std_score = scores.std()

        assert isinstance(mean_score, float)
        assert isinstance(std_score, float)
        assert std_score >= 0


class TestHyperparameterValidation:
    """Test hyperparameter validation"""

    @pytest.fixture
    def hp_data(self):
        """Create sample data for hyperparameter testing"""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = X[:, 0] + 0.5 * X[:, 1] + np.random.randn(100) * 0.2
        return X, y

    def test_max_depth_parameter(self, hp_data):
        """Test max_depth hyperparameter"""
        X, y = hp_data
        results = {}

        for depth in [1, 3, 5, 10]:
            model = DecisionTreeRegressor(max_depth=depth, random_state=42)
            model.fit(X, y)
            score = model.score(X, y)
            results[depth] = score

        assert len(results) == 4
        assert all(isinstance(s, float) for s in results.values())

    def test_n_estimators_parameter(self, hp_data):
        """Test n_estimators hyperparameter for Random Forest"""
        X, y = hp_data
        results = {}

        for n_est in [5, 10, 20, 50]:
            model = RandomForestRegressor(n_estimators=n_est, random_state=42, max_depth=3)
            model.fit(X, y)
            score = model.score(X, y)
            results[n_est] = score

        assert len(results) == 4

    def test_learning_rate_parameter(self, hp_data):
        """Test learning_rate hyperparameter for Gradient Boosting"""
        X, y = hp_data
        results = {}

        for lr in [0.01, 0.05, 0.1, 0.2]:
            model = GradientBoostingRegressor(
                learning_rate=lr,
                n_estimators=10,
                random_state=42,
                max_depth=2
            )
            model.fit(X, y)
            score = model.score(X, y)
            results[lr] = score

        assert len(results) == 4

    def test_invalid_max_depth(self, hp_data):
        """Test invalid max_depth parameter"""
        X, y = hp_data
        with pytest.raises(ValueError):
            model = DecisionTreeRegressor(max_depth=0)
            model.fit(X, y)

    def test_negative_n_estimators(self, hp_data):
        """Test negative n_estimators parameter"""
        with pytest.raises(ValueError):
            RandomForestRegressor(n_estimators=-1)


class TestModelComparison:
    """Test model comparison and selection"""

    @pytest.fixture
    def comparison_data(self):
        """Create data for model comparison"""
        np.random.seed(42)
        X = np.random.randn(100, 8)
        y = 2 * X[:, 0] - 1.5 * X[:, 1] + np.random.randn(100) * 0.5
        return X, y

    def test_compare_model_scores(self, comparison_data):
        """Test comparing scores across different models"""
        X, y = comparison_data
        models = {
            'LinearRegression': LinearRegression(),
            'DecisionTree': DecisionTreeRegressor(max_depth=5, random_state=42),
            'RandomForest': RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42),
            'GradientBoosting': GradientBoostingRegressor(n_estimators=10, max_depth=3, random_state=42)
        }

        scores = {}
        for name, model in models.items():
            model.fit(X, y)
            scores[name] = model.score(X, y)

        assert len(scores) == 4
        assert all(isinstance(s, float) for s in scores.values())

    def test_best_model_selection(self, comparison_data):
        """Test selecting best model based on score"""
        X, y = comparison_data
        models = {
            'LinearRegression': LinearRegression(),
            'DecisionTree': DecisionTreeRegressor(max_depth=5, random_state=42),
            'RandomForest': RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42),
        }

        scores = {}
        for name, model in models.items():
            model.fit(X, y)
            scores[name] = model.score(X, y)

        best_model = max(scores, key=scores.get)
        assert best_model in scores
        assert scores[best_model] >= min(scores.values())

    def test_model_ranking(self, comparison_data):
        """Test ranking models by performance"""
        X, y = comparison_data
        models = {
            'LinearRegression': LinearRegression(),
            'DecisionTree': DecisionTreeRegressor(max_depth=5, random_state=42),
            'RandomForest': RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42),
        }

        scores = {}
        for name, model in models.items():
            model.fit(X, y)
            scores[name] = model.score(X, y)

        ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        assert len(ranking) == 3
        assert ranking[0][1] >= ranking[1][1]
        assert ranking[1][1] >= ranking[2][1]


class TestModelPersistence:
    """Test model saving and loading"""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model"""
        np.random.seed(42)
        X = np.random.randn(50, 5)
        y = X[:, 0] + 0.5 * X[:, 1] + np.random.randn(50) * 0.1
        model = LinearRegression()
        model.fit(X, y)
        return model, X, y

    def test_model_state_after_training(self, trained_model):
        """Test that model has state after training"""
        model, X, y = trained_model
        assert hasattr(model, 'coef_')
        assert hasattr(model, 'intercept_')

    def test_model_prediction_consistency(self, trained_model):
        """Test that model makes consistent predictions"""
        model, X, y = trained_model
        pred1 = model.predict(X)
        pred2 = model.predict(X)

        np.testing.assert_array_equal(pred1, pred2)

    def test_model_coefficient_stability(self, trained_model):
        """Test that model coefficients remain stable"""
        model, X, y = trained_model
        coef1 = model.coef_.copy()

        pred = model.predict(X)

        coef2 = model.coef_.copy()
        np.testing.assert_array_equal(coef1, coef2)


class TestTrainingMetrics:
    """Test training metrics calculation"""

    @pytest.fixture
    def metric_data(self):
        """Create sample data for metrics testing"""
        np.random.seed(42)
        X = np.random.randn(50, 5)
        y = X[:, 0] + 0.5 * X[:, 1] + np.random.randn(50) * 0.1
        return X, y

    def test_r2_score_calculation(self, metric_data):
        """Test R² score calculation"""
        X, y = metric_data
        model = LinearRegression()
        model.fit(X, y)
        score = model.score(X, y)

        assert isinstance(score, float)
        assert -1 <= score <= 1

    def test_residuals_calculation(self, metric_data):
        """Test residuals calculation"""
        X, y = metric_data
        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        residuals = y - y_pred

        assert residuals.shape == y.shape
        assert residuals.mean() < 0.1

    def test_mae_calculation(self, metric_data):
        """Test Mean Absolute Error calculation"""
        X, y = metric_data
        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)

        mae = np.mean(np.abs(y - y_pred))
        assert isinstance(mae, (float, np.floating))
        assert mae >= 0

    def test_rmse_calculation(self, metric_data):
        """Test Root Mean Squared Error calculation"""
        X, y = metric_data
        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)

        rmse = np.sqrt(np.mean((y - y_pred) ** 2))
        assert isinstance(rmse, (float, np.floating))
        assert rmse >= 0
