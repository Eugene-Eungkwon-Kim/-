# fix_external_drive.ps1
# 외장하드 드라이브 자동 감지 및 경로 수정
# 사용법: .\.claude\fix_external_drive.ps1

param(
    [string]$ProjectName = "avm_project",
    [switch]$AutoFix = $false,
    [switch]$Verbose = $false
)

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  외장하드 드라이브 자동 감지 및 설정 수정 도구              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. 모든 드라이브 검색
Write-Host "🔍 외장하드 드라이브 검색 중..." -ForegroundColor Yellow

$drives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Name -match '^[A-Z]$' }
$externalDrive = $null
$projectPath = $null
$foundPaths = @()

# 2. avm_project 폴더 찾기
foreach ($drive in $drives) {
    $testPath = "$($drive.Name):\$ProjectName"
    if (Test-Path $testPath -ErrorAction SilentlyContinue) {
        $externalDrive = $drive.Name
        $projectPath = $testPath
        $foundPaths += $testPath
        Write-Host "  ✅ 발견: $testPath" -ForegroundColor Green
    }
}

if (-not $projectPath) {
    Write-Host ""
    Write-Host "❌ $ProjectName 폴더를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host ""
    Write-Host "확인사항:" -ForegroundColor Yellow
    Write-Host "  1. 외장하드가 컴퓨터에 연결되어 있습니까?"
    Write-Host "  2. 파일 탐색기에서 외장하드가 보입니까?"
    Write-Host "  3. 외장하드의 드라이브 문자는 무엇입니까? (D:, E:, F: 등)"
    Write-Host ""
    Write-Host "현재 연결된 드라이브:" -ForegroundColor Cyan
    Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free | Format-Table -AutoSize
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "✅ $ProjectName 폴더 위치: $projectPath" -ForegroundColor Green
Write-Host ""

# 3. 현재 설정 확인
$settingsFile = "$PSScriptRoot\settings.json"
$currentPath = $null

if (Test-Path $settingsFile) {
    try {
        $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
        $currentPath = $settings.workingDirectory
    } catch {
        Write-Host "⚠️  설정 파일 읽기 실패" -ForegroundColor Yellow
    }
}

if ($currentPath) {
    Write-Host "📋 현재 설정:" -ForegroundColor Cyan
    Write-Host "   $currentPath"
    Write-Host ""
    
    # 경로가 올바른지 확인
    $pathExists = Test-Path $currentPath
    if ($pathExists) {
        Write-Host "✅ 현재 경로는 접근 가능합니다." -ForegroundColor Green
        Write-Host ""
        
        # 최근 수정 날짜 확인
        $lastModified = (Get-Item $currentPath).LastWriteTime
        Write-Host "   마지막 수정: $lastModified" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host "❌ 현재 경로에 접근할 수 없습니다!" -ForegroundColor Red
        Write-Host ""
    }
}

# 4. 경로가 다른 경우 변경 제안
if ($currentPath -ne $projectPath) {
    Write-Host "📝 권장 변경:" -ForegroundColor Yellow
    Write-Host "   $currentPath → $projectPath" -ForegroundColor Yellow
    Write-Host ""
    
    $shouldChange = $AutoFix
    if (-not $AutoFix) {
        $response = Read-Host "경로를 변경하시겠습니까? (Y/n)"
        $shouldChange = ($response -ne "n")
    }
    
    if ($shouldChange) {
        try {
            # 설정 파일 업데이트
            if (Test-Path $settingsFile) {
                $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
            } else {
                $settings = @{}
            }
            
            $settings.workingDirectory = $projectPath
            $settings.relativePathBase = $projectPath
            $settings.projectRoot = $projectPath
            
            $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsFile -Force
            Write-Host ""
            Write-Host "✅ 설정 파일 업데이트 완료" -ForegroundColor Green
        } catch {
            Write-Host ""
            Write-Host "❌ 설정 파일 업데이트 실패: $_" -ForegroundColor Red
        }
    }
}

# 5. 작업 폴더로 이동
Write-Host ""
Write-Host "📂 작업 폴더로 이동 중..." -ForegroundColor Cyan

try {
    Set-Location $projectPath
    Write-Host "✅ 위치 변경: $(Get-Location)" -ForegroundColor Green
} catch {
    Write-Host "❌ 위치 변경 실패: $_" -ForegroundColor Red
    exit 1
}

# 6. Git 상태 확인
Write-Host ""
Write-Host "🔗 Git 저장소 확인 중..." -ForegroundColor Cyan

try {
    $gitStatus = git status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Git 저장소 정상" -ForegroundColor Green
        Write-Host ""
        Write-Host $gitStatus
    } else {
        Write-Host "⚠️  Git 오류:" -ForegroundColor Yellow
        Write-Host $gitStatus
    }
} catch {
    Write-Host "⚠️  Git 실행 실패: $_" -ForegroundColor Yellow
}

# 7. 최종 상태
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  🎉 준비 완료! 작업을 시작할 수 있습니다.                   ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "다음 명령어로 작업 시작:" -ForegroundColor Cyan
Write-Host "  python avm_project/scripts/test_full_pipeline.py" -ForegroundColor Gray
Write-Host "  git log --oneline -5" -ForegroundColor Gray
Write-Host ""
