# RTX 5050 메모리 전략 - 검증된 결론

**검증**: 6개 독립 조사 에이전트 교차검증 (18개 기술 주장, 모순 없음)
**작성일**: 2026-06-26

---

## 핵심 결론

> **RTX 5050의 8GB GDDR7은 물리적으로 고정 — "늘릴 수 없음". 대신 양자화/혼합정밀로 유효 용량을 4배까지 확대 가능.**

## 사실 확인

| 항목 | 검증 결과 | 근거 |
|------|----------|------|
| RTX 5050 VRAM | 8GB GDDR7 (모바일), 납땜 고정 | NVIDIA 공식 사양 |
| 작업관리자 "2GB" | Intel Iris Xe 내장 (별개 GPU) | LG그램 사양 |
| BIOS로 RTX 확대 | 불가 (Intel 내장만 DVMT 조절) | LG/Intel 문서 |
| 가상메모리로 확대 | 무효 (SSD라 100배 느림) | Linux DRM 문서 |

## 유효 용량 확대 (가능한 것)

| 기법 | 절감 | 프로젝트 연계 | 적합성 |
|------|------|--------------|--------|
| **INT8 양자화** | **4배** | Phase 13.2.5 (OpenVINO IR) ✅ | 최적 |
| FP16 혼합정밀 | 2배 | Phase 13.2 학습 | 권장 |
| Gradient Checkpointing | 활성화 50-70% | 대형 모델 학습 시 | 선택 |
| expandable_segments | 단편화 완화 | PyTorch 기본 적용 | 권장 |
| XGBoost subsample=0.6 | ~40% | Phase 13.2 | 권장 |

## 회피 (LG그램 부적합)

- **eGPU** (+8~24GB): 휴대성 파괴, RTX 50시리즈 TB4 불안정성 보고
- **멀티 GPU** (+8GB): RTX 5050 NVLink 미지원, 전력/발열 한계 (130W×2)
- **통합메모리 풀링**: 랜덤 접근 시 13배 느림 (PCIe 병목)

## 검증된 주의사항

- `set_per_process_memory_fraction()`은 **소프트 한도** (PyTorch #107667) — 스파이크 시 초과 가능. 멀티프로세스 격리는 cgroups 사용 권장.
- Unified Memory(`cudaMallocManaged`)는 페이지폴트 10-50μs 오버헤드 — 실시간 추론 부적합.

## 권장 파이프라인 (8GB 내 운영)

```
학습 (Phase 13.2):   FP16 혼합정밀 → 8GB로 충분
변환 (Phase 13.2.5): INT8 양자화 → 4배 절감
배포 (Phase 13.4):   NPU + OpenVINO → 저전력 추론
```

## 적용 코드

`scripts/gpu_config.py`:
- `select_training_device()` — RTX 5050 자동 선택 (Intel 내장 회피)
- `configure_torch_memory()` — 소프트 한도 + expandable_segments
- `get_memory_saving_options()` — 검증된 절감 기법 목록

---

**출처**: NVIDIA CUDA 문서, PyTorch GitHub 이슈, TensorRT, LG그램 사양, Linux DRM 커널 문서
