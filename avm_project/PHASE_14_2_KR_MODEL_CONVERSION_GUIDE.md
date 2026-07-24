# Phase 14.2.KR - Model Asset Conversion & Deployment Guide

**Date**: 2026-07-24  
**Status**: Ready to execute  
**Scope**: Converting 43.3MB ONNX models to platform-specific formats

---

## 📦 Model Assets Summary

**Source**: Phase 14.1.KR completed quantization outputs

### Model Files to Convert
```
output/models/korea/quantized_lite/
├── KR_nationwide_lite_int8.onnx         (42.7MB)
│
└── Regional (0.594MB total):
    ├── KR_seoul_lite_int8.onnx          (0.199MB)
    ├── KR_busan_lite_int8.onnx          (0.134MB)
    ├── KR_gyeonggi_lite_int8.onnx       (0.098MB)
    ├── KR_daegu_lite_int8.onnx          (0.081MB)
    └── KR_incheon_lite_int8.onnx        (0.082MB)
```

**Total**: 43.3MB (nationwide + 5 regions)

---

## 🍎 iOS Conversion: ONNX → Core ML

### Prerequisites
```bash
pip install coremltools onnx onnx-simplifier
```

### Conversion Script
```python
import coremltools as ct
import onnx

def convert_onnx_to_coreml(onnx_path: str, output_path: str) -> None:
    """Convert ONNX model to Core ML (.mlmodel)."""
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    
    ml_model = ct.convert(
        onnx_model,
        convert_to="mlprogram",
        compute_units=ct.ComputeUnit.ALL,
    )
    
    ml_model.save(output_path)
    print(f"✅ Converted: {onnx_path} → {output_path}")

# Convert nationwide model
convert_onnx_to_coreml(
    "output/models/korea/quantized_lite/KR_nationwide_lite_int8.onnx",
    "ios_app/Loan4U_iOS/Models/KR_nationwide_lite_int8.mlmodel"
)

# Convert regional models
for region in ["Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon"]:
    convert_onnx_to_coreml(
        f"output/models/korea/quantized_lite/KR_{region.lower()}_lite_int8.onnx",
        f"ios_app/Loan4U_iOS/Models/KR_{region.lower()}_lite_int8.mlmodel"
    )
```

### iOS Project Integration

**1. Add models to Xcode project:**
```
ios_app/Loan4U_iOS/
├── Models/
│   ├── KR_nationwide_lite_int8.mlmodel (42.7MB)
│   ├── KR_seoul_lite_int8.mlmodel      (0.199MB)
│   ├── KR_busan_lite_int8.mlmodel      (0.134MB)
│   ├── KR_gyeonggi_lite_int8.mlmodel   (0.098MB)
│   ├── KR_daegu_lite_int8.mlmodel      (0.081MB)
│   └── KR_incheon_lite_int8.mlmodel    (0.082MB)
```

**2. Xcode Project Settings:**
- Drag .mlmodel files into Xcode project
- Target: Loan4U_iOS
- Copy items if needed: ☑️
- Add to target: Loan4U_iOS ☑️

**3. Update MLModelService.swift:**
```swift
private func loadNationwideModel() throws {
    let modelURL = Bundle.main.url(forResource: "KR_nationwide_lite_int8", withExtension: "mlmodel")!
    nationalwideModel = try MLModel(contentsOf: modelURL)
}
```

**Expected Output:**
- App bundle size: ~45MB (43.3MB models + 1.7MB app code)
- Load time: <500ms (3-thread concurrent loading)

---

## 🤖 Android Conversion: ONNX → TensorFlow Lite

### Prerequisites
```bash
pip install tensorflow onnx-tf
```

### Conversion Strategy

**Option A: ONNX → TensorFlow → TFLite (Recommended)**
```python
import onnx
from onnx_tf.backend import prepare
import tensorflow as tf

def convert_onnx_to_tflite(onnx_path: str, output_path: str) -> None:
    """Convert ONNX → TF SavedModel → TFLite."""
    # Load ONNX
    onnx_model = onnx.load(onnx_path)
    
    # ONNX → TensorFlow
    tf_rep = prepare(onnx_model)
    tf_rep.export_graph("temp_savedmodel")
    
    # TensorFlow → TFLite
    converter = tf.lite.TFLiteConverter.from_saved_model("temp_savedmodel")
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.TFLITE_BUILTINS_INT8
    ]
    tflite_model = converter.convert()
    
    # Save
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    print(f"✅ Converted: {onnx_path} → {output_path}")
```

**Option B: ONNX → ONNX Runtime → Android (Fallback)**
- Use ONNX Runtime for Android if TFLite conversion fails
- Requires: `ai.onnxruntime:onnxruntime-android:latest`

### Android Asset Integration

**1. Create assets directory:**
```bash
mkdir -p android_app/Loan4U_Android/app/src/main/assets/models
```

**2. Copy converted models:**
```
android_app/Loan4U_Android/app/src/main/assets/models/
├── KR_nationwide_lite_int8.tflite    (42.7MB)
├── KR_seoul_lite_int8.tflite         (0.199MB)
├── KR_busan_lite_int8.tflite         (0.134MB)
├── KR_gyeonggi_lite_int8.tflite      (0.098MB)
├── KR_daegu_lite_int8.tflite         (0.081MB)
└── KR_incheon_lite_int8.tflite       (0.082MB)
```

**3. Add to build.gradle.kts:**
```kotlin
android {
    defaultConfig {
        // Allow large assets
    }
    
    packagingOptions {
        resources {
            excludes += "/META-INF/*.kotlin_module"
        }
    }
}
```

**4. MLModelService.kt already supports TFLite loading:**
```kotlin
private fun loadModelFile(filename: String): MappedByteBuffer {
    val assetFileDescriptor = context.assets.openFd(filename)
    val inputStream = FileInputStream(assetFileDescriptor.fileDescriptor)
    val fileChannel = inputStream.channel
    val startOffset = assetFileDescriptor.startOffset
    val declaredLength = assetFileDescriptor.declaredLength
    return fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
}
```

**Expected Output:**
- APK size: ~55MB (43.3MB models + 11.7MB app code)
- Load time: <800ms (single-thread asset loading)

---

## ✅ Pre-Deployment Verification

### iOS Verification

**1. Model Loading Test:**
```swift
func testModelLoads() {
    let modelService = MLModelService()
    XCTAssertTrue(modelService.isLoaded, "Should load models")
    XCTAssertNil(modelService.loadingError)
}
```

**2. Inference Test:**
```swift
func testNationwideModelPredicts() {
    let features: [String: Double] = [
        "area_sqm": 85, "year_built": 2010, ...  // 22 features
    ]
    let result = modelService.predict(features: features)
    XCTAssertNotNil(result)
    XCTAssertGreater(result!.predictedPrice, 0)
}
```

**3. App Size Check:**
- Build for App Store
- Archive → Organizer
- Estimated app size: ~45MB

### Android Verification

**1. Model Loading Test:**
```kotlin
@Test
fun testModelLoads() = runTest {
    val service = MLModelService(context)
    assertTrue(service.isLoaded.value, "Should load models")
}
```

**2. Inference Test:**
```kotlin
@Test
fun testNationwideModelPredicts() = runTest {
    val features = mapOf(
        "area_sqm" to 85f, "year_built" to 2010f, ...  // 22 features
    )
    val result = service.predict(features)
    assertNotNull(result)
    assertTrue(result!!.predictedPrice > 0)
}
```

**3. APK Size Check:**
- Run: `./gradlew bundleRelease`
- Check: `build/outputs/bundle/release/`
- Estimated size: ~55MB

---

## 🚀 Deployment Checklist

### Before Model Integration
- [ ] ONNX models verified in `output/models/korea/quantized_lite/`
- [ ] Conversion environment ready (Python + TensorFlow/ONNX)
- [ ] Target directories created (iOS Models/, Android assets/)

### After iOS Conversion
- [ ] 6 .mlmodel files created (42.7MB + 0.594MB)
- [ ] Models added to Xcode project
- [ ] Bundle identifiers configured
- [ ] Code signing certificates ready
- [ ] App size <50MB verified

### After Android Conversion
- [ ] 6 .tflite files created (43.3MB total)
- [ ] Models copied to assets folder
- [ ] build.gradle.kts configured
- [ ] APK size ~55MB verified
- [ ] Keystore created and secured

### Testing
- [ ] iOS: Unit tests pass (5/5 FeatureEngineering tests)
- [ ] Android: Unit tests pass (7/7 FeatureEngineering tests)
- [ ] iOS: Prediction flow working (input → result)
- [ ] Android: Prediction flow working (input → result)
- [ ] Both: Caching mechanism functional (24h TTL)

### Store Submission
- [ ] iOS: App Store app description written
- [ ] iOS: Screenshots and preview video prepared
- [ ] iOS: Privacy policy URL ready
- [ ] Android: Google Play app description written
- [ ] Android: Store listing images prepared
- [ ] Android: Consent form (if data collection)

---

## 📊 Expected Metrics

### Performance (After Integration)

| Metric | iOS | Android |
|--------|-----|---------|
| Model Load (first run) | <500ms | <800ms |
| Prediction Inference | 5-15ms | 8-20ms |
| Cache Hit | <5ms | <5ms |
| Memory Usage | ~80MB | ~100MB |
| Battery (per prediction) | <0.1% | <0.15% |

### Size Metrics

| Component | iOS | Android |
|-----------|-----|---------|
| Models | 43.3MB | 43.3MB |
| App Code | ~1.7MB | ~11.7MB |
| **Total** | **~45MB** | **~55MB** |

### Coverage

| Test Suite | Target | Status |
|-----------|--------|--------|
| Unit Tests (Feature Eng.) | 100% | ✅ Ready (5/7) |
| Integration Tests | Core flows | 🔄 Ready to add |
| UI Tests | Input→Result | 🔄 Ready to add |

---

## 🔄 Post-Deployment Support

### Monitoring
- Track prediction accuracy per region
- Monitor app crash rates
- Watch model inference latency
- Alert on > 15% accuracy drop

### Future Updates
- Phase 14.3: Real data retraining (if approved)
- Phase 14.4: OpenVINO IR export (NPU support)
- Phase 14.5: Advanced features (comparative pricing, market trends)

---

## 📝 Timeline

```
Today (2026-07-24)
├── 09:00: Model conversion scripts ready
├── 12:00: iOS .mlmodel files created + integrated
├── 14:00: Android .tflite files created + integrated
├── 16:00: Unit tests passing (both platforms)
├── 17:00: Integration tests passing
└── 18:00: Ready for App Store/Play Store submission

Tomorrow (2026-07-25)
├── 09:00: Final performance profiling
├── 11:00: Store submission metadata finalized
├── 12:00: iOS submitted to App Store
├── 13:00: Android submitted to Google Play
│
└── 2-3 days: Store review + approval

Production (2026-07-27/28)
├── iOS: App Store release
├── Android: Google Play release
└── Monitor: User feedback + accuracy metrics
```

---

**Status**: Foundation complete. Model conversion ready to execute.

**Next**: Execute conversion scripts and integrate assets into both projects.
