# Loan4U - GPU 0 (Intel iGPU) 점유 프로세스 진단 및 개선 도구
# 사용법: PowerShell에서 실행
#   powershell -ExecutionPolicy Bypass -File find_gpu0_process.ps1
# 목적: 자판 발열 원인인 GPU 0 점유 작업을 찾아 RTX 5050 전환 안내

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Loan4U GPU 0 발열 진단 도구" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1단계: 설치된 GPU 목록 확인
Write-Host "[1] 설치된 GPU 확인" -ForegroundColor Yellow
$gpus = Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion
$index = 0
foreach ($gpu in $gpus) {
    $vram = if ($gpu.AdapterRAM -gt 0) { "{0:N0} MB" -f ($gpu.AdapterRAM / 1MB) } else { "공유" }
    $type = if ($gpu.Name -match "RTX|GTX|NVIDIA") { "[전용 - 쿨링 좋음]" } else { "[내장 - CPU발열]" }
    Write-Host "  GPU $index : $($gpu.Name) - $vram $type" -ForegroundColor White
    $index++
}
Write-Host ""

# 2단계: GPU 엔진별 사용률 (프로세스 단위) - 성능 카운터
Write-Host "[2] GPU 점유 프로세스 분석 중... (약 5초)" -ForegroundColor Yellow
try {
    $counters = (Get-Counter "\GPU Engine(*)\Utilization Percentage" -ErrorAction Stop).CounterSamples |
        Where-Object { $_.CookedValue -gt 1 }

    # phys_0 = 보통 Intel 내장, phys_1 = RTX
    $gpu0 = $counters | Where-Object { $_.InstanceName -match "phys_0" }
    $gpu1 = $counters | Where-Object { $_.InstanceName -match "phys_1" }

    Write-Host ""
    Write-Host "  === GPU 0 (Intel 내장 - 발열원) 점유 프로세스 ===" -ForegroundColor Red
    $gpu0Procs = @{}
    foreach ($c in $gpu0) {
        if ($c.InstanceName -match "pid_(\d+)_") {
            $pid_val = $matches[1]
            $gpu0Procs[$pid_val] += $c.CookedValue
        }
    }
    if ($gpu0Procs.Count -eq 0) {
        Write-Host "    (점유 프로세스 없음)" -ForegroundColor Gray
    } else {
        foreach ($p in ($gpu0Procs.GetEnumerator() | Sort-Object Value -Descending)) {
            $proc = Get-Process -Id $p.Key -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { "PID $($p.Key)" }
            Write-Host ("    {0,-25} 사용률 {1:N0}%  (PID {2})" -f $name, $p.Value, $p.Key) -ForegroundColor White
        }
    }

    Write-Host ""
    Write-Host "  === GPU 1 (RTX 5050 - 전용쿨링) 점유 프로세스 ===" -ForegroundColor Green
    $gpu1Procs = @{}
    foreach ($c in $gpu1) {
        if ($c.InstanceName -match "pid_(\d+)_") {
            $pid_val = $matches[1]
            $gpu1Procs[$pid_val] += $c.CookedValue
        }
    }
    if ($gpu1Procs.Count -eq 0) {
        Write-Host "    (점유 프로세스 없음 - RTX가 놀고 있음!)" -ForegroundColor Gray
    } else {
        foreach ($p in ($gpu1Procs.GetEnumerator() | Sort-Object Value -Descending)) {
            $proc = Get-Process -Id $p.Key -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { "PID $($p.Key)" }
            Write-Host ("    {0,-25} 사용률 {1:N0}%  (PID {2})" -f $name, $p.Value, $p.Key) -ForegroundColor White
        }
    }
} catch {
    Write-Host "  ⚠ 성능 카운터 접근 실패: $_" -ForegroundColor Red
    Write-Host "  → 작업관리자(Ctrl+Shift+Esc) → 세부정보 → GPU 열 추가로 수동 확인" -ForegroundColor Yellow
}

# 3단계: 개선 안내
Write-Host ""
Write-Host "[3] 개선 방법" -ForegroundColor Yellow
Write-Host "  GPU 0(Intel)에서 작업이 돌고 있다면 → RTX 5050으로 전환:" -ForegroundColor White
Write-Host ""
Write-Host "  방법 A (Windows 설정 - 권장):" -ForegroundColor Cyan
Write-Host "    설정 > 시스템 > 디스플레이 > 그래픽" -ForegroundColor Gray
Write-Host "    > 해당 앱 추가 > 옵션 > '고성능(RTX 5050)' 선택" -ForegroundColor Gray
Write-Host ""
Write-Host "  방법 B (Python 작업):" -ForegroundColor Cyan
Write-Host "    set CUDA_VISIBLE_DEVICES=1   (실행 전 입력)" -ForegroundColor Gray
Write-Host ""
Write-Host "  방법 C (NVIDIA 제어판 전역):" -ForegroundColor Cyan
Write-Host "    바탕화면 우클릭 > NVIDIA 제어판 > 3D 설정 관리" -ForegroundColor Gray
Write-Host "    > 기본 그래픽 프로세서 > '고성능 NVIDIA 프로세서'" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 진단 완료" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
