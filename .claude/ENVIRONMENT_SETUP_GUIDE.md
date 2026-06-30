# Claude Code 에이전트 환경 설정 가이드

**목적**: 모든 에이전트가 공통으로 참조하는 환경 설정 문서  
**작성일**: 2026-06-26  
**버전**: 1.0.0  
**대상**: 모든 Claude 에이전트

---

## 📌 중요: 에이전트 입장 확인

모든 Claude 에이전트가 이 프로젝트에서 작업을 시작할 때 **반드시** 이 문서를 읽으세요.

---

## 🖥️ **환경 구성 - Windows 사용자**

### ⚠️ **드라이브 매핑 문제 및 해결**

#### **문제 증상**
```
❌ 작업 폴더에 접근 불가
❌ "파일을 찾을 수 없음" 오류
❌ D드라이브가 응답하지 않음
❌ 외장하드 인식 오류
```

#### **원인**
```
외장하드 드라이브 문자가 변경됨
├─ 이전: D드라이브 (외장하드)
└─ 현재: E드라이브 (또는 다른 문자)

하지만 프로젝트 경로는 여전히 D:\avm_project 로 설정됨
```

#### **즉시 해결 (5분)**

**Step 1: 현재 드라이브 확인**
```powershell
# PowerShell (관리자 권한)
Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used

# 외장하드 드라이브 문자 확인 (예: E:, F:, G: 등)
```

**Step 2: 프로젝트 폴더 찾기**
```powershell
# 외장하드 드라이브로 이동 (E: 라고 가정)
cd E:\

# avm_project 폴더 있는지 확인
dir | grep avm_project

# 또는
Test-Path E:\avm_project
```

**Step 3: Claude Code 설정 변경**
```
Method A (GUI - 권장):
1. Claude Code 앱 열기
2. Settings (⚙️) → Project Settings
3. Working Directory 변경
   D:\avm_project → E:\avm_project (확인된 경로)
4. 저장 → 앱 재시작

Method B (파일 직접 수정):
1. .claude/settings.json 편집
2. "workingDirectory": "D:\\avm_project" 
   → "workingDirectory": "E:\\avm_project"
3. 저장
```

**Step 4: 검증**
```powershell
# 작업 폴더로 이동
cd E:\avm_project

# Git 상태 확인
git status

# 출력 예상:
# On branch claude/eloquent-meitner-lqxu9r
# Your branch is up to date with 'origin/claude/eloquent-meitner-lqxu9r'.
# nothing to commit, working tree clean
```

**Step 5: 프로젝트 재개**
```powershell
# 테스트 실행
python avm_project/scripts/test_full_pipeline.py

# Git 작업 재개
git status
```

---

### 🔧 **자동 경로 수정 스크립트**

외장하드 드라이브를 자동으로 감지하고 경로를 수정하는 PowerShell 스크립트:

**파일**: `.claude/fix_external_drive.ps1`

```powershell
# fix_external_drive.ps1
# 외장하드 드라이브 자동 감지 및 경로 수정

param(
    [string]$ProjectName = "avm_project",
    [switch]$AutoFix = $false
)

Write-Host "🔍 외장하드 드라이브 검색 중..." -ForegroundColor Cyan

# 1. 모든 드라이브 확인
$drives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Name -match '^[A-Z]$' }
$externalDrive = $null
$projectPath = $null

# 2. avm_project 폴더 찾기
foreach ($drive in $drives) {
    $testPath = "$($drive.Name):\$ProjectName"
    if (Test-Path $testPath) {
        $externalDrive = $drive.Name
        $projectPath = $testPath
        Write-Host "✅ 발견: $projectPath" -ForegroundColor Green
        break
    }
}

if (-not $projectPath) {
    Write-Host "❌ $ProjectName 폴더를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "외장하드가 연결되어 있는지 확인하세요." -ForegroundColor Yellow
    exit 1
}

# 3. 현재 설정 확인
$settingsFile = "$PSScriptRoot\settings.json"
if (Test-Path $settingsFile) {
    $settings = Get-Content $settingsFile | ConvertFrom-Json
    $currentPath = $settings.workingDirectory
    
    Write-Host ""
    Write-Host "현재 설정: $currentPath" -ForegroundColor Yellow
    Write-Host "새로운 경로: $projectPath" -ForegroundColor Cyan
    
    if ($currentPath -eq $projectPath) {
        Write-Host "✅ 이미 올바르게 설정되어 있습니다!" -ForegroundColor Green
        exit 0
    }
}

# 4. 경로 변경
if ($AutoFix -or (Read-Host "경로를 변경하시겠습니까? (Y/n)") -ne "n") {
    Set-Location $projectPath
    Write-Host "✅ 작업 폴더 변경됨: $(Get-Location)" -ForegroundColor Green
    
    # Git 상태 확인
    $gitStatus = git status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Git 저장소 정상" -ForegroundColor Green
        Write-Host $gitStatus
    } else {
        Write-Host "⚠️ Git 확인 필요:" -ForegroundColor Yellow
        Write-Host $gitStatus
    }
}

Write-Host ""
Write-Host "🎉 준비 완료! 작업을 시작할 수 있습니다." -ForegroundColor Green
```

**실행 방법:**
```powershell
# 1. PowerShell (관리자 권한)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser

# 2. 스크립트 실행
.\.claude\fix_external_drive.ps1

# 3. 자동 수정 (확인 없이)
.\.claude\fix_external_drive.ps1 -AutoFix
```

---

### 📌 **드라이브 문제 예방**

#### **드라이브 문자 영구 고정**

**Windows에서:**
```
1. 디스크 관리 열기 (Ctrl+X → "디스크 관리")
2. 외장하드 우클릭
3. "드라이브 문자 및 경로 변경..."
4. 드라이브 문자 선택 (예: D:)
5. 확인 → 적용

이후 외장하드는 항상 같은 문자로 인식됨
```

---

## 🌐 **환경 구성 - 원격 실행 환경 (Linux/Cloud)**

### **환경 정보**
```
- OS: Linux
- Platform: Cloud Container (ephemeral)
- Git: 자동 설정
- Python: 3.10+
```

### **경로 설정**
```
작업 디렉토리: /home/user/-/avm_project/
Git 저장소: /home/user/-/ (루트)
브랜치: claude/eloquent-meitner-lqxu9r
```

### **확인 방법**
```bash
pwd                          # 현재 위치
ls -la avm_project/          # 프로젝트 구조
git status                   # Git 상태
git log --oneline -5         # 최근 커밋
```

---

## ✅ **에이전트 시작 체크리스트**

모든 에이전트는 프로젝트 작업을 시작하기 전에 다음을 확인하세요:

### **Windows 환경**
- [ ] 외장하드 드라이브 문자 확인 (D: 또는 E: 또는?)
- [ ] `E:\avm_project` (또는 올바른 경로) 존재 확인
- [ ] Claude Code Working Directory 설정 확인
- [ ] `git status` 실행 가능 확인
- [ ] 파일 접근 가능 확인

### **Linux/Cloud 환경**
- [ ] `/home/user/-/avm_project/` 접근 가능 확인
- [ ] Git 브랜치: `claude/eloquent-meitner-lqxu9r` 확인
- [ ] `git status` 실행 확인
- [ ] 파일 읽기/쓰기 권한 확인

### **공통 확인사항**
- [ ] `.claude/EXECUTION_POLICY.md` 읽음
- [ ] `CLAUDE.md` 읽음
- [ ] 필요한 의존성 설치됨 (`requirements.txt`)
- [ ] 코드 품질 기준 이해함 (50줄/함수, 100% 타입 힌트)

---

## 🚨 **문제 발생 시**

### **문제**: Git 커밋 실패
```
해결:
1. git status 확인
2. 작업 디렉토리 경로 확인
3. 파일 권한 확인 (chmod +x scripts/*.py)
```

### **문제**: 파일을 찾을 수 없음
```
해결:
1. 현재 위치 확인 (pwd)
2. 드라이브/경로 매핑 확인
3. 파일 존재 확인 (ls avm_project/scripts/)
```

### **문제**: Python 모듈 임포트 오류
```
해결:
1. requirements.txt 설치 확인
pip install -r avm_project/requirements.txt

2. PYTHONPATH 확인
export PYTHONPATH=/home/user/-:$PYTHONPATH (Linux)

3. 모듈 경로 확인
python -c "import sys; print(sys.path)"
```

### **문제**: 권한 오류 (Permission Denied)
```
해결 (Linux):
chmod -R 755 avm_project/
chmod -R u+w avm_project/

해결 (Windows):
우클릭 → 속성 → 보안 → 전체 제어 허용
```

---

## 📞 **에이전트 간 커뮤니케이션**

프로젝트 작업 중 문제가 발생하면:

1. **이 문서 먼저 확인**
2. **EXECUTION_POLICY.md 참조**
3. **Git 히스토리 확인**: `git log --oneline -10`
4. **최근 커밋 확인**: `git show HEAD`
5. **다른 에이전트 작업 확인**: `git log --all --oneline -20`

---

## 🎯 **에이전트별 역할 분담**

| 에이전트 | 담당 영역 | 필수 확인사항 |
|---------|---------|-------------|
| 개발 에이전트 | 코드 작성/수정 | 경로 설정, Git 상태 |
| QA 에이전트 | 테스트 작성 | 테스트 환경 설정 |
| DevOps 에이전트 | CI/CD 설정 | GitHub Actions 접근 |
| 문서 에이전트 | 문서화 | Markdown 형식 준수 |

---

## 📋 **주요 프로젝트 문서 위치**

모든 에이전트가 참조해야 할 문서:

```
.claude/
├── EXECUTION_POLICY.md          ⭐ 필수 읽기
├── ENVIRONMENT_SETUP_GUIDE.md   (이 파일)
└── settings.json

CLAUDE.md                        ⭐ 필수 읽기

avm_project/
├── README.md                    프로젝트 개요
├── docs/
│   ├── COMPLETE_DEPLOYMENT_GUIDE.md
│   ├── TEST_QA_QC_PLAN.md
│   ├── PHASE_13_GPU_NPU_PIPELINE.md
│   └── GPU_MEMORY_VERIFIED.md
├── scripts/                     모든 구현 코드
└── tests/                       모든 테스트 코드
```

---

## 🔄 **에이전트 인계 절차**

한 에이전트에서 다른 에이전트로 작업을 넘길 때:

**Step 1: 현재 상태 정리**
```bash
git status                    # 커밋되지 않은 변경사항 확인
git log --oneline -5          # 최근 작업 확인
```

**Step 2: 모든 변경사항 커밋**
```bash
git add .
git commit -m "[작업명] 설명

자세한 설명...

Co-Authored-By: Claude ... <noreply@anthropic.com>"
```

**Step 3: 푸시**
```bash
git push -u origin claude/eloquent-meitner-lqxu9r
```

**Step 4: 다음 에이전트에게 인계**
- 최종 커밋 해시 공유
- 현재 상태 설명
- 남은 작업 목록 제시
- 이 문서 참조

---

## ✨ **환경 준비 완료 확인**

모든 확인사항을 완료했으면:

```
✅ 경로 설정 완료
✅ Git 상태 정상
✅ 파일 접근 가능
✅ 정책 문서 읽음
✅ 준비 완료!
```

이제 작업을 시작할 수 있습니다. 🚀

---

**최종 업데이트**: 2026-06-26  
**버전**: 1.0.0  
**관리자**: Loan4U AVM 팀

---

## 🎓 **부록: 명령어 빠른 참조**

### **Windows (PowerShell)**
```powershell
# 드라이브 확인
Get-PSDrive -PSProvider FileSystem

# 외장하드로 이동
cd E:\avm_project

# Git 상태
git status

# 최근 커밋
git log --oneline -5

# 환경 수정 스크립트
.\.claude\fix_external_drive.ps1 -AutoFix
```

### **Linux/Cloud**
```bash
# 현재 위치
pwd

# Git 상태
git status

# 최근 커밋
git log --oneline -5

# 브랜치 확인
git branch -vv

# 모든 파일 확인
find avm_project/ -type f | head -20
```

---

**모든 에이전트는 이 가이드를 북마크하세요!** 📌
