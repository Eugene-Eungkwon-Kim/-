#!/usr/bin/env python3
"""
Loan4U Phase 13.5 - Model Registry & Continuous Learning
Version control, A/B testing, and automated monthly retraining.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


@dataclass
class ModelMetadata:
    """Model version metadata."""
    version: str
    country: str
    algorithm: str
    r2_score: float
    mape: float
    training_date: str
    model_size_mb: float
    ir_size_mb: float
    status: str = "active"
    notes: str = ""


@dataclass
class RegistryEntry:
    """Registry entry for model version."""
    model_id: str
    metadata: ModelMetadata
    model_path: str
    ir_path: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ModelRegistry:
    """Manage model versions, A/B tests, and deployments."""

    def __init__(self, registry_dir: str = "output/model_registry") -> None:
        """Initialize model registry."""
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "registry.json"
        self.entries: List[RegistryEntry] = self._load_registry()

    def _load_registry(self) -> List[RegistryEntry]:
        """Load existing registry from disk."""
        if not self.registry_file.exists():
            return []

        try:
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
                return [RegistryEntry(**entry) for entry in data]
        except Exception as e:
            log.warning(f"Failed to load registry: {e}")
            return []

    def _save_registry(self) -> None:
        """Persist registry to disk."""
        try:
            data = [asdict(entry) for entry in self.entries]
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            log.info(f"Registry saved: {len(self.entries)} entries")
        except Exception as e:
            log.error(f"Failed to save registry: {e}")

    def register_model(self, metadata: ModelMetadata, model_path: str,
                      ir_path: str) -> str:
        """Register new model version."""
        model_id = f"{metadata.country}_{metadata.algorithm}_{metadata.version}"

        # Check for duplicate
        if any(e.model_id == model_id for e in self.entries):
            log.warning(f"Model already registered: {model_id}")
            return model_id

        entry = RegistryEntry(
            model_id=model_id,
            metadata=metadata,
            model_path=model_path,
            ir_path=ir_path
        )
        self.entries.append(entry)
        self._save_registry()

        log.info(f"✅ Registered: {model_id} (R²={metadata.r2_score:.3f})")
        return model_id

    def get_active_model(self, country: str, algorithm: str) -> Optional[RegistryEntry]:
        """Get latest active model for country/algorithm."""
        candidates = [
            e for e in self.entries
            if e.metadata.country == country
            and e.metadata.algorithm == algorithm
            and e.metadata.status == "active"
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda e: e.metadata.training_date)

    def set_model_status(self, model_id: str, status: str) -> bool:
        """Update model status (active/inactive/archived)."""
        for entry in self.entries:
            if entry.model_id == model_id:
                entry.metadata.status = status
                self._save_registry()
                log.info(f"Updated {model_id} status: {status}")
                return True

        log.warning(f"Model not found: {model_id}")
        return False

    def list_models(self, country: Optional[str] = None) -> List[Dict[str, object]]:
        """List registered models."""
        entries = self.entries

        if country:
            entries = [e for e in entries if e.metadata.country == country]

        result = []
        for entry in sorted(entries, key=lambda e: e.metadata.training_date, reverse=True):
            result.append({
                "model_id": entry.model_id,
                "version": entry.metadata.version,
                "country": entry.metadata.country,
                "algorithm": entry.metadata.algorithm,
                "r2": entry.metadata.r2_score,
                "mape": entry.metadata.mape,
                "status": entry.metadata.status,
                "date": entry.metadata.training_date,
            })

        return result

    def get_stats(self) -> Dict[str, object]:
        """Get registry statistics."""
        active = sum(1 for e in self.entries if e.metadata.status == "active")
        countries = set(e.metadata.country for e in self.entries)
        algorithms = set(e.metadata.algorithm for e in self.entries)

        return {
            "total_models": len(self.entries),
            "active_models": active,
            "countries": list(countries),
            "algorithms": list(algorithms),
            "avg_r2": sum(e.metadata.r2_score for e in self.entries) / len(self.entries) if self.entries else 0,
        }


class ContinuousLearning:
    """Automated retraining pipeline."""

    def __init__(self, registry: ModelRegistry) -> None:
        """Initialize continuous learning."""
        self.registry = registry

    def should_retrain(self, country: str, algorithm: str,
                      days_since_training: int = 30) -> bool:
        """Check if model needs retraining."""
        active = self.registry.get_active_model(country, algorithm)
        if not active:
            return True

        try:
            train_date = datetime.fromisoformat(active.metadata.training_date)
            days_old = (datetime.now() - train_date).days
            return days_old >= days_since_training
        except Exception:
            return False

    def schedule_retraining(self, country: str) -> Dict[str, object]:
        """Determine which models need retraining."""
        algorithms = ['XGBoost', 'LightGBM', 'GradientBoosting']
        to_retrain = []

        for algo in algorithms:
            if self.should_retrain(country, algo):
                to_retrain.append(algo)

        return {
            "country": country,
            "models_to_retrain": to_retrain,
            "count": len(to_retrain),
        }


def main() -> None:
    """Demonstrate model registry usage."""
    registry = ModelRegistry()

    # Example: Register a model
    metadata = ModelMetadata(
        version="v13.2.1",
        country="KR",
        algorithm="XGBoost",
        r2_score=0.862,
        mape=0.092,
        training_date=datetime.now().isoformat(),
        model_size_mb=8.5,
        ir_size_mb=2.1
    )

    model_id = registry.register_model(
        metadata,
        "output/trained_models/xgboost_KR.pkl",
        "output/models_ir/xgboost_KR_ir"
    )

    # Get stats
    stats = registry.get_stats()
    print(f"\n{'='*50}")
    print("Model Registry Status")
    print(f"{'='*50}")
    print(f"Total models: {stats['total_models']}")
    print(f"Active models: {stats['active_models']}")
    print(f"Avg R²: {stats['avg_r2']:.3f}")

    # List models
    models = registry.list_models("KR")
    print(f"\n한국(KR) 모델 목록:")
    for m in models:
        print(f"  {m['model_id']}: R²={m['r2']:.3f}, MAPE={m['mape']:.1%}")

    # Continuous learning
    cl = ContinuousLearning(registry)
    schedule = cl.schedule_retraining("KR")
    print(f"\n재훈련 필요: {schedule['models_to_retrain']}")


if __name__ == '__main__':
    main()
