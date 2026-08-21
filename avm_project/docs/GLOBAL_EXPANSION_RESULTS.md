# Phase 13.X Global Expansion Results

**Date**: 2026-07-18
**Status**: ✅ All 9 countries complete (Waves 1–3)
**Architecture**: StackingRegressor (XGBoost + LightGBM + GradientBoosting + RandomForest + ExtraTrees → Ridge meta) — identical to KR production model

## Model Performance Summary

| Country | Wave | Test MAPE | Target | Test R² | ONNX Match | Status |
|---------|------|-----------|--------|---------|------------|--------|
| KR | baseline | 8.62% | <10.5% | 0.9732 | 100.0% | ✅ PASS |
| BR | 1 | 6.77% | <10% | 0.9690 | 100.0% | ✅ PASS |
| SG | 1 | 6.73% | <10% | 0.9694 | 100.0% | ✅ PASS |
| HK | 1 | 6.75% | <10% | 0.9698 | 100.0% | ✅ PASS |
| UK | 2 | 4.38% | <10% | 0.9888 | 100.0% | ✅ PASS |
| DE | 2 | 6.64% | <10% | 0.9674 | 100.0% | ✅ PASS |
| AU | 2 | 8.33% | <10% | 0.9506 | 99.8% | ✅ PASS |
| CA | 2 | 8.40% | <10% | 0.9510 | 100.0% | ✅ PASS |
| TH | 3 | 8.20% | <10% | 0.9562 | 100.0% | ✅ PASS |

All countries meet the R² >0.84 and MAPE <10.5% global targets.
UK achieves the best accuracy (strict ±5% tolerance market → lowest
simulation noise). AU/CA/TH sit higher due to relaxed tolerance bands
(±10–15%), consistent with country policy in `TOLERANCE_MAP`.

## Pipeline Architecture

```
phase13_global_pipeline.py --country {CC}
  1. collect_country_data()   feature-driven price simulation
  2. engineer_features()      city/type dummies, age polynomial,
                              accessibility, economic interactions
  3. train_and_save()         Stacking Ensemble + metadata JSON

phase13_stacking_converter.py --leak-patterns "price_local,indexed_price"
  4. ONNX conversion          skl2onnx + onnxmltools GBM converters
  5. validation               500-sample pkl vs ONNX comparison

phase13_inference_engine.py / phase13_inference_api.py
  6. serving                  NPU→GPU→CPU auto-fallback, REST API
```

Adding a new country requires only one `COUNTRY_CONFIGS` entry
(cities, price base, tolerance, economic indicators).

## Artifacts (gitignored — regenerate via pipeline)

- `data/raw/{CC}_raw.csv` — 20,000 records per country
- `data/processed/{CC}_engineered.csv` — engineered feature matrices
- `output/models/{cc}_production_v1.0.pkl` + metadata JSON
- `output/converted_models/{cc}_production_v1.0.onnx` + conversion report

## Known Limitations

- All non-KR data is **simulated** (feature-driven synthetic prices).
  Real API integration (Seloger, FIPE, URA, HM Land Registry, etc.)
  is scheduled as Phase 13.6.
- Simulation noise is capped at min(tolerance, 10%), so real-market
  MAPE will be higher; the pipeline and serving infrastructure are
  what these results validate.

## Next Steps

1. **Phase 13.6**: Replace simulation with live data source integration
2. **Phase 13.5**: Multi-country model registry + weighted ensemble
3. **Phase 14**: CI/CD automation and monitoring
