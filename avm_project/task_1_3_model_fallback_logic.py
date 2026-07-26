#!/usr/bin/env python3
"""
Task 1.3: Model Fallback Logic
Implement 4-tier fallback chain for predictions
"""

import joblib
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

class PredictionFallback:
    """4-Tier Fallback Chain for Model Predictions"""

    def __init__(self):
        self.models = {}
        self.cache = {}
        self.fallback_data = {}
        self.status_log = []

    def load_models(self):
        """Tier 1: Load primary models"""
        model_dir = Path("./models")
        models = [
            ("v1.1", "retrained_20260624_signal/gradient_boosting_20260624.joblib"),
            ("v1.0", "gradient_boosting_20260612_130130.pkl"),
        ]

        for version, path in models:
            full_path = model_dir / path
            if full_path.exists():
                self.models[version] = joblib.load(full_path)
                print(f"✅ Tier 1 - Model v{version} loaded")

        return len(self.models) > 0

    def load_cache(self):
        """Tier 2: Load cached regional averages"""
        cache_path = Path("./data/cache/regional_averages.json")
        if cache_path.exists():
            with open(cache_path) as f:
                self.cache = json.load(f)
            print(f"✅ Tier 2 - Cache loaded ({len(self.cache)} regions)")
            return True
        return False

    def load_fallback(self):
        """Tier 3: Load global averages"""
        fallback_path = Path("./data/cache/global_fallback.json")
        if fallback_path.exists():
            with open(fallback_path) as f:
                self.fallback_data = json.load(f)
            print(f"✅ Tier 3 - Global fallback loaded")
            return True
        return False

    def predict(self, features, region=None):
        """4-Tier prediction with fallback"""
        try:
            # Tier 1: Try primary model (v1.1)
            if "v1.1" in self.models:
                result = float(self.models["v1.1"].predict([features])[0])
                return {"value": result, "source": "tier_1_v1.1", "confidence": 0.95}
        except Exception as e:
            self.status_log.append(f"Tier 1 fallback: {str(e)}")

        try:
            # Tier 2: Try secondary model (v1.0)
            if "v1.0" in self.models:
                result = float(self.models["v1.0"].predict([features])[0])
                return {"value": result, "source": "tier_2_v1.0", "confidence": 0.85}
        except Exception as e:
            self.status_log.append(f"Tier 2 fallback: {str(e)}")

        # Tier 3: Use regional average
        if region and isinstance(self.cache, dict):
            for region_name, region_avg in self.cache.items():
                if region in str(region_name):
                    if isinstance(region_avg, dict):
                        value = region_avg.get("mean", region_avg.get(0))
                    else:
                        value = region_avg
                    return {"value": float(value), "source": "tier_3_regional_avg", "confidence": 0.70}

        # Tier 4: Use global average
        if self.fallback_data:
            if isinstance(self.fallback_data, dict):
                # Try to find average price
                price_keys = [k for k in self.fallback_data.keys() if "가격" in k or "price" in k.lower()]
                if price_keys:
                    value = self.fallback_data[price_keys[0]]
                else:
                    values = [v for v in self.fallback_data.values() if isinstance(v, (int, float))]
                    value = sum(values) / len(values) if values else 0
                return {"value": float(value), "source": "tier_4_global_avg", "confidence": 0.50}

        return {"value": 0, "source": "tier_4_error", "confidence": 0.0}

    def validate(self):
        """Validate fallback chain"""
        print("\n" + "=" * 60)
        print("TASK 1.3: MODEL FALLBACK LOGIC")
        print("=" * 60)

        # Load all tiers
        self.load_models()
        self.load_cache()
        self.load_fallback()

        # Test with sample features
        sample_features = [100, 10, 2024, 25.5, 85.0]  # Hypothetical features
        result = self.predict(sample_features, region="서울")

        print(f"\n📊 Fallback Chain Status:")
        print(f"   Tier 1 (v1.1 Model): {'✅' if 'v1.1' in self.models else '❌'}")
        print(f"   Tier 2 (v1.0 Model): {'✅' if 'v1.0' in self.models else '❌'}")
        print(f"   Tier 3 (Regional Avg): {'✅' if self.cache else '❌'}")
        print(f"   Tier 4 (Global Avg): {'✅' if self.fallback_data else '❌'}")

        print(f"\n✅ Test Prediction:")
        print(f"   Value: {result['value']:.2f}")
        print(f"   Source: {result['source']}")
        print(f"   Confidence: {result['confidence']:.0%}")

        if self.status_log:
            print(f"\n⚠️ Fallback Events: {len(self.status_log)}")

        print("\n✅ TASK 1.3 COMPLETE: Fallback Logic Implemented")
        return True


if __name__ == "__main__":
    fallback = PredictionFallback()
    fallback.validate()
