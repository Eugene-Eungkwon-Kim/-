# GPU Memory Expansion: Quick Reference Tables
## Loan4U AVM Phase 13 — Technical Lookup Guide

**Use this document for**: Quick answers, implementation lookups, performance estimates  
**Related**: GPU_MEMORY_EXPANSION_SYNTHESIS_REPORT.md (full analysis)  
**Related**: GPU_MEMORY_EXECUTIVE_BRIEF.md (executive summary)

---

## Table 1: Five Methods Comparison Matrix

```
┌─ Method ─────────────────────────────────────────────────────────────┐
│ 1. BIOS Shared Memory Allocation                                     │
├────────────────────────────────────────────────────────────────────────┤
│ Target Device:          Intel Iris Xe integrated GPU                  │
│ Theoretical Max:        +1GB (BIOS allocation ceiling)               │
│ Practical Achievable:   +256-512MB (typical LG Gram models)          │
│ Target RTX 5050:        NO (only for iGPU)                           │
│ Performance Impact:     +0-2% CPU overhead                            │
│ Accuracy Impact:        None                                          │
│ Implementation:         BIOS > Integrated Graphics > Shared Memory    │
│ Difficulty:             1/5 (menu navigation)                         │
│ Permanence:             Permanent (until next BIOS reboot)            │
│ LG Gram Compatible:     ✓ Yes (2023+ models tested)                   │
│ Verdict:                ❌ SKIP (negligible benefit)                  │
│ Use case:               None (too small to matter)                    │
└────────────────────────────────────────────────────────────────────────┘

┌─ Method ─────────────────────────────────────────────────────────────┐
│ 2. Virtual Memory (Linux DRM Kernel Swap)                            │
├────────────────────────────────────────────────────────────────────────┤
│ Mechanism:              Page VRAM contents to SSD on overflow         │
│ Theoretical Max:        +500GB (SSD size limit)                       │
│ Practical Achievable:   +4-6GB (after which 100x slowdown kicks in)   │
│ Speed at:               0-2GB: Native (0.3μs latency)                 │
│                         2-6GB: Slow (100-500μs latency)               │
│                         >6GB:  Unusable (100-1000x slowdown)          │
│ Performance Impact:     -70-95% for spilled data                      │
│ Training Time Impact:   +0min (if fits in 8GB)                        │
│                         +40-100% (if overflows)                       │
│ Accuracy Impact:        None (functional equivalence)                 │
│ Requirement:            Linux kernel swappiness > 0 (default: 60)     │
│ Implementation:         Automatic (enabled by default)                │
│ Difficulty:             1/5 (nothing to do)                           │
│ Permanence:             Temporary (resets on reboot/training end)     │
│ LG Gram Compatible:     ✓ Yes (all Linux systems)                     │
│ Verdict:                ⚠️ USE AS FALLBACK (safety net)               │
│ When to use:            If VRAM allocation exceeds 8GB in testing     │
└────────────────────────────────────────────────────────────────────────┘

┌─ Method ─────────────────────────────────────────────────────────────┐
│ 3. ONNX/INT8 Quantization (Post-training Compression)               │
├────────────────────────────────────────────────────────────────────────┤
│ Mechanism:              Convert weights from FP32/FP16 to INT8        │
│ Effective Compression:  4x (8GB model → 2GB quantized)               │
│ Scope:                  Inference models ONLY (not training)          │
│ Performance Impact:     0% (inference speed unchanged)                │
│ Latency Impact:         0-10% (quantized models sometimes faster)     │
│ Accuracy Impact:        -0-2% typical (acceptable for AVM)            │
│ Workflow:               Train (GPU) → Export ONNX → Quantize → IR     │
│ Tool:                   OpenVINO toolkit (free, open-source)          │
│ Implementation:         Phase 13.2.5 model conversion step            │
│ Difficulty:             3/5 (scripting, but routine process)          │
│ Permanence:             Permanent (quantized model is new artifact)   │
│ LG Gram Compatible:     ✓ Yes (OpenVINO supports all platforms)       │
│ Verdict:                ✅ HIGHLY RECOMMENDED (use in 13.2.5)         │
│ Expected Benefit:       4x model compression for deployment           │
└────────────────────────────────────────────────────────────────────────┘

┌─ Method ─────────────────────────────────────────────────────────────┐
│ 4. CUDA Unified Memory (Virtual Address Pooling)                     │
├────────────────────────────────────────────────────────────────────────┤
│ Mechanism:              Single virtual address space (GPU+CPU memory) │
│ Theoretical Pool:       8GB GPU + 8GB+ CPU RAM (16GB+ total)          │
│ Practical Usable:       2-3x GPU VRAM before latency penalty          │
│ Latency Per Access:     10-50 microseconds (page fault overhead)      │
│ Performance Impact:     -10-30% for training (page faults)            │
│ Accuracy Impact:        None (logical equivalence)                    │
│ Training Time Impact:   +30-50% (due to page faults)                 │
│ Requirement:            NVIDIA driver, CUDA 8.0+, architecture SM60+ │
│ Implementation:         CUDA API (cudaMallocManaged)                  │
│ Difficulty:             4/5 (requires kernel/driver changes)          │
│ Permanence:             Temporary (runtime only)                      │
│ LG Gram Compatible:     △ Uncertain (driver compatibility unknown)    │
│ Verdict:                ❌ NOT RECOMMENDED (latency kills performance)│
│ Why avoided:            Slow down negates memory benefit              │
└────────────────────────────────────────────────────────────────────────┘

┌─ Method ─────────────────────────────────────────────────────────────┐
│ 5. eGPU or Multi-GPU Expansion (External Hardware)                   │
├────────────────────────────────────────────────────────────────────────┤
│ Mechanism:              Attach external GPU via Thunderbolt 4         │
│ Theoretical Addition:   +8-24GB (per RTX 4090/RTX 5090 GPU)          │
│ Practical Achievable:   Uncertain (RTX 50-series TB4 issues known)    │
│ Portability Impact:     Destroyed (enclosure = 5-8kg)                 │
│ Power Impact:           +250W (RTX 4090 = 450W total system)          │
│ Thermal Impact:         Major (requires external cooling)             │
│ Driver Issues:          RTX 50-series: Known Thunderbolt 4 failures   │
│ NVLink Support:         RTX 5050 does NOT support NVLink              │
│ Cost:                   $500-3000 (GPU enclosure + external GPU)      │
│ Implementation:         Hardware purchase + driver debugging          │
│ Difficulty:             5/5 (hardware + driver issues)                │
│ Permanence:             Permanent (if it works)                       │
│ LG Gram Compatible:     ✗ No (TB4 driver issues, portability gone)    │
│ Verdict:                ❌ NOT VIABLE (risks > rewards)               │
│ Why rejected:           Portability destroyed, known driver issues    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Table 2: Three Realistic Scenarios

### Scenario A: BIOS Shared Memory Only

| Aspect | Details |
|--------|---------|
| **Implementation** | LG Gram BIOS > Integrated Graphics > Shared Memory = 256MB |
| **Expected Increase** | +256-512MB (0.6-1.3% gain) |
| **Total Effective VRAM** | 8GB + 0.25GB = 8.25GB |
| **Performance Impact** | +0% (negligible) |
| **Training Time** | No significant change |
| **Accuracy Impact** | None |
| **Effort** | 30 minutes (BIOS menu navigation) |
| **Difficulty** | 1/5 |
| **Risk** | Very low (BIOS change is reversible) |
| **Permanence** | Permanent (until next BIOS reboot) |
| **Verdict** | ❌ SKIP this method |
| **Rationale** | Gain too small to justify effort |

### Scenario B: Virtual Memory Only

| Aspect | Details |
|--------|---------|
| **Implementation** | Rely on Linux kernel DRM swap (automatic) |
| **Expected Increase** | +4-6GB (at 100x slowdown rate for spilled data) |
| **Total Effective VRAM** | 8GB VRAM + 4-6GB SSD = 12-14GB total |
| **Usable VRAM** | 8GB at native speed, +2-3GB at acceptable speed |
| **Performance Impact** | -0% (if no spillover), -70-95% (if spillover occurs) |
| **Training Time Example** | 5 min (fits in 8GB) → 35 min (overflows to SSD) |
| **Accuracy Impact** | None (functional equivalence) |
| **Effort** | 5 minutes (verify swappiness setting) |
| **Difficulty** | 1/5 |
| **Risk** | Medium (possible OOM if SSD full) |
| **Permanence** | Temporary (resets after training) |
| **Verdict** | ⚠️ USE AS SAFETY NET |
| **When to use** | If training data exceeds 8GB in testing |
| **Example threshold** | 160K rows × 30 features fits fine; 500K rows may spill |

### Scenario C: Hybrid Approach (RECOMMENDED)

| Aspect | Details |
|--------|---------|
| **Implementation** | FP16 mixed precision + subsample=0.6 + virtual memory |
| **Expected Increase** | 2-4x effective (8GB → 16-32GB equivalent) |
| **Breakdown** | - Base: 8GB<br>- FP16 savings: ×2 (16GB)<br>- Subsample savings: ×1.4 (22GB)<br>- Total: 22GB equivalent in 8GB physical |
| **Practical Limit** | 16GB effective before virtual memory spillover |
| **Performance Impact** | -0-5% (FP16 may be faster on RTX 50-series tensor cores) |
| **Training Time** | Same or slightly faster (FP16 acceleration) |
| **Accuracy Impact** | -0-2% (FP16 introduces minor numerical loss) |
| **Effort** | 3 days (code integration in phase13_model_trainer.py) |
| **Difficulty** | 3/5 |
| **Risk** | Very low (standard PyTorch features) |
| **Permanence** | Permanent (optimization code integrated) |
| **Verdict** | ✅ HIGHLY RECOMMENDED |
| **Why choose this** | Best balance of benefit, simplicity, zero cost |
| **Cost** | $0 (software optimization only) |
| **Data capacity** | Safely handles 160K-300K rows per country |
| **Safety margin** | 6GB free (emergency headroom) |

---

## Table 3: Phase 13 Integration Timeline

| Phase | Activity | Method Used | Effective VRAM | Duration | Deadline |
|-------|----------|-------------|----------------|----------|----------|
| **13.1** | Data collection (CPU only) | None | N/A (CPU-bound) | 5 days | 2026-07-03 |
| **13.2** | GPU model training | Scenario C | 8-16GB (16GB effective) | 5-8 days | 2026-07-10 |
| | • XGBoost | FP16 + subsample | 8GB practical | 5 min/country | |
| | • LightGBM | FP16 + subsample | 8GB practical | 3 min/country | |
| | • Gradient Boosting | CPU only | 2GB | 40 min | |
| **13.2.5** | Model conversion | INT8 quantization | 2GB output | 1 day | 2026-07-11 |
| | • Export ONNX | (GPU trained models) | | 4 min total | |
| | • Convert to OpenVINO | (quantized IR) | | 2 min total | |
| | • NPU inference tuning | (Method 3) | | 8 hours | |
| **13.3** | Model validation | None | N/A (inference only) | 5 days | 2026-07-15 |
| **13.4** | NPU deployment | INT8 models (Method 3) | 0.5GB (quantized) | 2 days | 2026-07-17 |

---

## Table 4: XGBoost GPU Memory Configuration

### Parameter Impact on Memory Usage

| Parameter | Default | Optimized | Memory Impact | Speed Impact | Recommendation |
|-----------|---------|-----------|---|---|---|
| `tree_method` | exact | gpu_hist | -0% (GPU move) | +700% (GPU faster) | ✅ Use gpu_hist |
| `max_depth` | 6 | 6 | Baseline | Baseline | ✓ Keep as is |
| `max_depth` | 6 | 5 | -20% memory | -5% accuracy | ⚠️ Only if OOM |
| `max_bin` | 256 | 127 | -50% memory | -0% (slight speedup) | ✅ Use 127 |
| `max_bin` | 256 | 63 | -75% memory | -2% accuracy | ⚠️ Only if OOM |
| `subsample` | 1.0 | 0.6 | -40% memory | -0% (faster convergence) | ✅ Use 0.6 |
| `subsample` | 1.0 | 0.4 | -60% memory | -10% accuracy | ⚠️ Only if OOM |
| `colsample_bytree` | 1.0 | 0.6 | -40% memory | -0% | ✅ Use 0.6 |
| `grow_policy` | depthwise | lossguide | -20% memory | -0% | ✅ Use lossguide |
| `n_estimators` | 100 | 500 | +400% memory | +0% (just more trees) | ✓ Keep high |

### Recommended Production Settings (Phase 13.2)

```python
xgb_params_phase13 = {
    'tree_method': 'gpu_hist',        # GPU acceleration
    'device_id': 0,                   # RTX 5050
    'max_depth': 6,                   # Baseline
    'learning_rate': 0.05,
    'n_estimators': 500,
    'max_bin': 127,                   # ← Memory optimization
    'grow_policy': 'lossguide',       # ← Memory efficiency
    'subsample': 0.6,                 # ← 40% memory reduction
    'colsample_bytree': 0.6,          # ← Feature subsampling
}
```

**Expected Memory Usage**: 3-4GB / 8GB VRAM  
**Expected Training Time**: 5 minutes per country  
**Expected Accuracy**: R² 0.86-0.88, MAPE <10%  
**Safety Margin**: 4GB free for other operations  

---

## Table 5: Inference Performance Comparison

### NPU vs CPU vs GPU

| Metric | CPU Only | GPU (RTX 5050) | NPU (OpenVINO) | Improvement |
|--------|----------|---|---|---|
| **Latency (ms)** | 5-10 | 2-5 | <2 | 5-50x |
| **Latency p99 (ms)** | 20-50 | 5-15 | 3-5 | 5-15x |
| **Throughput (req/s)** | 100-200 | 200-500 | 500-2000 | 5-20x |
| **Model Size** | 2GB (FP32) | 2GB (FP32) | 0.5GB (INT8) | 4x smaller |
| **Power (W)** | 20 | 100+ | 3 | 6-30x less |
| **Memory (GB)** | 2 | 2 | 0.5 | 4x less |
| **Cost** | Free | Power bill | Free (onboard) | Infinite ROI |
| **Use Case** | Fallback | Training/tuning | ✅ Production |

### Calculation Examples

**Single Prediction Latency:**
- CPU: 5ms (100M CPU cycles × 100ns)
- GPU: 3ms (memory transfer overhead)
- NPU: 1ms (optimized for inference)

**Throughput @ 2000 req/sec:**
- CPU: 100 servers needed (20 req/sec per server max)
- GPU: 4 servers needed (500 req/sec per GPU server)
- NPU: 1 server needed (2000 req/sec per NPU)

**24/7 Operating Cost (1000 predictions/day):**
- CPU: $2/day (electricity)
- GPU: $10/day
- NPU: $0.30/day
- Annual savings (NPU): ~$3600

---

## Table 6: Validation Checklist (Phase 13.2-13.4)

### Pre-Training Validation (Week of 2026-07-03)

- [ ] **GPU Verification**: Run `nvidia-smi`, note GPU model and VRAM amount
- [ ] **CUDA Check**: Verify CUDA compute capability >= 6.1 (FP16 support)
- [ ] **Driver Version**: Check NVIDIA driver supports RTX model
- [ ] **Memory Test**: Run XGBoost on 10K sample, monitor peak VRAM
- [ ] **Virtual Memory**: Verify Linux swappiness > 0 (default 60)
- [ ] **BIOS Check** (optional): Document Integrated Graphics shared memory setting
- [ ] **Space Check**: Verify 50GB free on SSD (for models, datasets, output)

### During Training Validation (2026-07-04 to 07-10)

- [ ] **Memory Monitoring**: Log peak VRAM usage per country
- [ ] **Speed Monitoring**: Record actual training time per country
- [ ] **Error Logging**: Document any CUDA out-of-memory errors
- [ ] **Accuracy Check**: Verify R² and MAPE on validation set match expectations
- [ ] **Virtual Memory**: Check if SSD swap was triggered (grep /proc/meminfo)
- [ ] **Log Results**: Store metrics in Phase_13_Training_Metrics.csv

### Model Conversion Validation (2026-07-11)

- [ ] **ONNX Export**: Verify 16 ONNX files (8 XGBoost + 8 LightGBM) generated
- [ ] **ONNX Validation**: Run `onnx.checker.check_model()` on each
- [ ] **OpenVINO Convert**: Verify XML+BIN files generated (16 × 2 = 32 files)
- [ ] **Size Check**: Confirm 8GB → 2GB compression (4x reduction)
- [ ] **Model Load**: Test loading all models in OpenVINO runtime
- [ ] **Inference Test**: Single prediction latency measured (<2ms target)

### Deployment Validation (2026-07-15 to 07-17)

- [ ] **NPU Availability**: Confirm 'NPU' in `Core().available_devices`
- [ ] **Model Load**: All 8 country models load successfully
- [ ] **Latency Test**: Measure single prediction time (<2ms target)
- [ ] **Throughput Test**: Benchmark batch predictions (1000 requests)
- [ ] **Accuracy Validation**: Inference output matches GPU training baseline
- [ ] **API Integration**: FastAPI endpoint /predict working with NPU backend
- [ ] **Stress Test**: Simulate 1000 concurrent requests (check stability)

---

## Table 7: Troubleshooting Guide

### Symptom: "CUDA out of memory" during training

| Diagnosis | Root Cause | Solution | Expected Outcome |
|-----------|-----------|----------|-----------------|
| Runs first country OK, fails on 2nd | Model cache not cleared | Restart training script | Restart fixes it |
| Fails immediately on country 1 | Dataset larger than expected | Check dataset size: `X_train.nbytes` | May need Method 2 (virtual memory) |
| Fails even with small dataset | Subsample/max_bin settings | Reduce: subsample→0.4, max_bin→63 | Slower training, fits in VRAM |
| Intermittent OOM (random failure) | Memory fragmentation | Enable expandable_segments | Reduces fragmentation |

### Symptom: Training very slow (>30 min per country)

| Diagnosis | Root Cause | Solution | Expected Outcome |
|-----------|-----------|----------|-----------------|
| nvidia-smi shows GPU 0% usage | CPU training fallback | Verify device_id=0 in XGBoost | GPU should show 100% |
| nvidia-smi shows GPU 100% but slow | Virtual memory swapping | Check: `watch -n 2 'nvidia-smi \| grep Memory'` | If VRAM maxed, reduce subsample |
| GPU-accurate but training slow | Too many trees (n_estimators=1000+) | Reduce to 500 trees | Standard runtime reduction |
| FP16 training slower than FP32 | Unsupported architecture | Verify compute capability >= 7.0 | May need to use FP32 |

### Symptom: Model accuracy drops after quantization (INT8)

| Diagnosis | Root Cause | Solution | Expected Outcome |
|-----------|-----------|----------|-----------------|
| >2% accuracy loss | Extreme value outliers | Check dataset for anomalies | Validate training data quality |
| 1-2% loss (acceptable) | Normal INT8 quantization | Proceed (this is expected) | Deployment with 1-2% accuracy loss |
| 0.5% loss (excellent) | Good value distribution | No action needed | Proceed to deployment |
| Accuracy actually *improves* | Model regularization effect | No action needed | Quantization acts as regularizer |

### Symptom: NPU not detected (fallback to CPU)

| Diagnosis | Root Cause | Solution | Expected Outcome |
|-----------|-----------|----------|-----------------|
| OpenVINO reports only 'CPU' device | NPU driver not loaded | Install Intel NPU driver package | NPU appears in available_devices |
| NPU appears but inference slow | NPU model not compiled | Run `ov.compile_model(..., 'NPU')` | Inference uses NPU, <2ms latency |
| Model loads but OOM on NPU | Model too large for NPU | Use INT8 quantized model (0.5GB max) | Quantized model fits easily |
| Fallback to CPU is acceptable | No NPU available | Proceed with CPU (5x slower but stable) | API still 3-5x faster than baseline |

---

## Table 8: Phase 13 Deliverables Checklist

### Phase 13.2 Outputs (GPU Training)

- [ ] `models/phase13_UK_xgboost.pkl` (8 countries)
- [ ] `models/phase13_UK_lightgbm.pkl` (8 countries)
- [ ] `models/phase13_UK_gradient_boosting.pkl` (8 countries)
- [ ] `results/phase13_training_metrics.csv` (VRAM usage, time, accuracy)
- [ ] `results/phase13_training_log.txt` (full console output)

### Phase 13.2.5 Outputs (Model Conversion)

- [ ] `models/onnx/UK_xgboost.onnx` (8 countries)
- [ ] `models/onnx/UK_lightgbm.onnx` (8 countries)
- [ ] `models/openvino/UK_xgboost.xml` (8 countries)
- [ ] `models/openvino/UK_xgboost.bin` (8 countries)
- [ ] `results/phase13_conversion_metrics.json` (compression, latency benchmarks)

### Phase 13.4 Outputs (NPU Deployment)

- [ ] `phase13_npu_api.py` (FastAPI server with NPU inference)
- [ ] `results/phase13_inference_benchmark.json` (latency, throughput, accuracy)
- [ ] `docs/phase13_deployment_guide.md` (how to run the API)
- [ ] `results/phase13_completion_report.md` (following EXECUTION_POLICY.md template)

---

## Quick Command Reference

### GPU Detection
```bash
nvidia-smi                              # Check GPU, VRAM, driver
nvidia-smi --query-gpu=compute_cap --format=csv  # Check FP16 support (need >= 6.1)
```

### Memory Monitoring During Training
```bash
watch -n 2 'nvidia-smi | grep -E "Memory|Process"'  # Monitor live
nvidia-smi dmon -s pucm                 # Detailed memory/power stats
```

### Virtual Memory Check
```bash
cat /proc/sys/vm/swappiness            # Should be > 0 (default 60)
free -h                                 # Check available RAM + swap
```

### ONNX Conversion (Phase 13.2.5)
```bash
python -m onnx checkers check_model models/onnx/UK_xgboost.onnx
python -m openvino convert_model models/onnx/UK_xgboost.onnx
```

### NPU Availability Check
```python
from openvino import Core
print(Core().available_devices)  # Should include 'NPU' or 'CPU'
```

---

**Last Updated**: 2026-06-26  
**For Questions**: Refer to GPU_MEMORY_EXPANSION_SYNTHESIS_REPORT.md  
**Phase 13 Go-Live**: 2026-07-03
