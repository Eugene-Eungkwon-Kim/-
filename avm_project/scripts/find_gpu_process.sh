#!/bin/bash
# Loan4U - GPU 점유 프로세스 진단 (Linux/WSL)
# 사용법: bash find_gpu_process.sh
# 목적: GPU별 점유 프로세스 확인 후 RTX 5050 전환 안내

echo "============================================"
echo " Loan4U GPU 점유 프로세스 진단 (Linux)"
echo "============================================"
echo ""

# 1단계: NVIDIA GPU (RTX 5050) 프로세스
echo "[1] RTX 5050 (NVIDIA) 점유 프로세스"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null \
        | awk -F',' '{printf "    %-30s %s VRAM (PID%s)\n", $2, $3, $1}'
    [ -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null)" ] \
        && echo "    (점유 프로세스 없음 - RTX가 놀고 있음)"
else
    echo "    ⚠ nvidia-smi 없음 (드라이버 미설치)"
fi
echo ""

# 2단계: Intel GPU (내장) 프로세스 - intel_gpu_top 필요
echo "[2] Intel 내장 GPU (발열원) 점유 확인"
if command -v intel_gpu_top &> /dev/null; then
    echo "    intel_gpu_top 실행 (3초 샘플)..."
    timeout 3 intel_gpu_top -o - 2>/dev/null | head -20
else
    echo "    intel_gpu_top 미설치 → 설치: sudo apt install intel-gpu-tools"
    echo "    또는: sudo intel_gpu_top 으로 실시간 확인"
fi
echo ""

# 3단계: 전체 GPU 사용 프로세스 (fuser)
echo "[3] DRI 디바이스 점유 프로세스 (전체 GPU)"
if [ -d /dev/dri ]; then
    for card in /dev/dri/card*; do
        echo "    $card:"
        sudo fuser -v "$card" 2>/dev/null | tail -n +1 || echo "      (권한 필요: sudo)"
    done
else
    echo "    /dev/dri 없음"
fi
echo ""

# 4단계: 개선 안내
echo "[4] 개선 방법"
echo "    작업을 RTX 5050으로 강제 지정:"
echo ""
echo "    # NVIDIA만 보이게 (Python/CUDA 작업)"
echo "    export CUDA_VISIBLE_DEVICES=1"
echo ""
echo "    # PRIME offload (특정 앱을 RTX로)"
echo "    __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia <앱>"
echo ""
echo "    # 영구 설정: ~/.bashrc 에 export CUDA_VISIBLE_DEVICES=1 추가"
echo ""
echo "============================================"
echo " 진단 완료"
echo "============================================"
