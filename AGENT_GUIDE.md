# 🚀 Claude 에이전트 - 시작 가이드

**모든 Claude 에이전트가 이 프로젝트에서 작업을 시작할 때 반드시 읽으세요!**

---

## ⚠️ **중요: 드라이브 문제 해결 (Windows 사용자 필수)**

### **문제**: Windows에서 외장하드 드라이브 문자가 변경됨
```
D드라이브 → E드라이브 변경
프로젝트는 여전히 D:\avm_project 로 설정 → 접근 불가
```

### **즉시 해결 (1줄)**

**Windows PowerShell (관리자 권한):**
```powershell
.\.claude\fix_external_drive.ps1 -AutoFix
```

**Linux/Cloud:**
```bash
cd /home/user/-/avm_project && git status
```

---

## ✅ **모든 에이전트의 3단계 체크리스트**

### **Step 1️⃣: 환경 확인 (1분)**

#### Windows
```powershell
# 자동 수정
.\.claude\fix_external_drive.ps1 -AutoFix

# 또는 수동 확인
cd E:\avm_project
git status  # working tree clean 이어야 함
```

#### Linux/Cloud
```bash
cd /home/user/-/avm_project
git status  # working tree clean 이어야 함
```

### **Step 2️⃣: 필수 문서 읽기 (2분)**

다음 문서를 이 순서대로 읽기:

1. **`.claude/AGENT_STARTUP_CHECKLIST.md`** ← 5분 체크
2. **`.claude/ENVIRONMENT_SETUP_GUIDE.md`** ← 상세 가이드
3. **`.claude/EXECUTION_POLICY.md`** ← 개발 정책
4. **`CLAUDE.md`** ← 프로젝트 가이드

### **Step 3️⃣: 작업 시작 (1분)**

```bash
# 최근 커밋 확인
git log --oneline -3

# 테스트 실행
python avm_project/scripts/test_full_pipeline.py

# 작업 시작!
```

---

## 📚 **에이전트를 위한 가이드 문서 위치**

```
프로젝트 루트 (/ 에이전트가 볼 수 있음)
├─ AGENT_GUIDE.md ← 이 파일 (모든 에이전트 필독)
├─ CLAUDE.md ← 프로젝트 설정
├─ README.md ← 프로젝트 개요
│
.claude/ 폴더 (세션 설정)
├─ AGENT_STARTUP_CHECKLIST.md ← 5분 시작 체크
├─ ENVIRONMENT_SETUP_GUIDE.md ← 상세 환경 설정
├─ EXECUTION_POLICY.md ← 개발 정책 (필수)
├─ fix_external_drive.ps1 ← Windows 자동 수정
└─ settings.json ← 세션 설정
│
avm_project/ 폴더
├─ docs/ ← 프로젝트 문서들
├─ scripts/ ← 모든 코드 파일
├─ tests/ ← 테스트 코드
└─ requirements.txt ← 의존성
```

---

## 🎯 **작업 시작 전 체크리스트**

모든 항목이 ✅ 되어야 작업 시작 가능:

### **환경**
- [ ] **드라이브 확인** (D드라이브가 아님!)
  - Windows: E드라이브? 또는 자동 수정 실행?
  - Linux: `/home/user/-/avm_project`?
- [ ] **Git 정상**
  ```bash
  git status  # working tree clean?
  ```
- [ ] **파일 접근 가능**
  ```bash
  ls avm_project/scripts/  # 파일 보임?
  ```

### **지식**
- [ ] **AGENT_STARTUP_CHECKLIST.md 읽음**
- [ ] **ENVIRONMENT_SETUP_GUIDE.md 읽음**
- [ ] **EXECUTION_POLICY.md 읽음**
- [ ] **코드 기준 이해함** (50줄/함수, 100% 타입 힌트)

### **준비**
- [ ] **최근 커밋 확인**
  ```bash
  git log --oneline -5
  ```
- [ ] **브랜치 확인**
  ```bash
  git branch -vv  # claude/eloquent-meitner-lqxu9r?
  ```

---

## 🚨 **문제 발생 시 (즉시 해결)**

### **❌ 드라이브 오류 (Windows)**
```powershell
# 자동 수정 실행
.\.claude\fix_external_drive.ps1 -AutoFix

# 또는 수동
cd E:\avm_project
git status
```

### **❌ Git 오류**
```bash
git status              # 현재 상태
git remote -v          # 원격 저장소 확인
git branch -vv         # 브랜치 확인
```

### **❌ 파일 접근 안 됨**
```bash
# 경로 확인
pwd                    # /home/user/-/avm_project 인가?
ls -la avm_project/    # 파일 보임?
```

---

## 📞 **다른 에이전트와의 커뮤니케이션**

### **현재 프로젝트 상태**
```bash
git log --oneline -5       # 최근 작업
git log --all --oneline    # 모든 브랜치 작업 확인
```

### **작업 인계**
```bash
# 1. 변경사항 커밋
git add .
git commit -m "[작업명] 설명..."

# 2. 푸시
git push -u origin claude/eloquent-meitner-lqxu9r

# 3. 다음 에이전트에게: 최종 커밋 해시 공유
git log --oneline -1  # 예: 934c32c
```

---

## 🎓 **에이전트 온보딩 (새 에이전트)**

**첫 번째 에이전트가 이 프로젝트에 올 때:**

1. 이 파일 읽기 ← 지금 읽는 것
2. `.claude/AGENT_STARTUP_CHECKLIST.md` 읽기 (5분)
3. 자동 수정 스크립트 실행 (Windows만)
4. 필수 문서 읽기
5. `git status` 확인
6. 작업 시작!

**예상 시간: 20분 이내**

---

## ✨ **빠른 명령어 참조**

### **확인**
```bash
pwd                    # 현재 위치
git status            # Git 상태
git log -1            # 최근 커밋
git branch -vv        # 브랜치
```

### **작업**
```bash
git add .             # 변경사항 추가
git commit -m "..."   # 커밋
git push              # 푸시
```

### **테스트**
```bash
python avm_project/scripts/test_full_pipeline.py
```

---

## 🎯 **이 프로젝트의 3가지 핵심 원칙**

### **1️⃣ 코드 품질**
- 함수 최대 50줄
- 100% 타입 힌트
- 최소 주석 (WHY만)

### **2️⃣ 자동화**
- 매월 자동 재훈련
- CI/CD 파이프라인
- 실시간 모니터링

### **3️⃣ 협력**
- Git으로 중앙 관리
- 명확한 커밋 메시지
- 문서화

---

## 📋 **작업 시작 확인 신호**

모든 다음이 ✅ 이면 작업 시작 가능:

```
✅ 드라이브/경로 설정 완료
✅ Git 상태 정상
✅ 파일 접근 가능
✅ 필수 문서 읽음
✅ 코드 기준 이해함

→ 작업 시작! 🚀
```

---

## 🔗 **관련 문서**

모든 에이전트는 **이 순서대로** 읽기:

1. **이 파일** (AGENT_GUIDE.md) ← 시작점
2. **`.claude/AGENT_STARTUP_CHECKLIST.md`** ← 5분 체크
3. **`.claude/ENVIRONMENT_SETUP_GUIDE.md`** ← 상세 가이드
4. **`.claude/EXECUTION_POLICY.md`** ← 필수 정책
5. **`CLAUDE.md`** ← 프로젝트 가이드
6. **`README.md`** ← 프로젝트 개요

---

**이 파일을 북마크하세요!** 📌

모든 새 에이전트가 가장 먼저 봐야 할 파일입니다.

---

**버전**: 1.0.0  
**날짜**: 2026-06-26  
**대상**: 모든 Claude 에이전트
