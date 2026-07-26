# 에이전트 시작 체크리스트

**목적**: 모든 Claude 에이전트가 작업 시작 전 확인해야 할 사항  
**버전**: 1.0.0  
**업데이트**: 2026-06-26

---

## 🚀 **시작 전 5분 체크**

### **Step 1️⃣: 환경 설정 (1분)**

#### Windows 사용자
```powershell
# 자동 수정 실행 (강력권장)
.\.claude\fix_external_drive.ps1 -AutoFix

# 또는 수동 확인
cd E:\avm_project  # 드라이브 확인!
git status        # Git 정상?
```

#### Linux/Cloud 사용자
```bash
cd /home/user/-/avm_project
pwd                    # /home/user/-/avm_project 확인?
git status            # Git 정상?
```

### **Step 2️⃣: 필수 문서 읽기 (2분)**

**반드시 읽어야 할 문서**:
- [ ] `.claude/ENVIRONMENT_SETUP_GUIDE.md` - 환경 설정
- [ ] `.claude/EXECUTION_POLICY.md` - 개발 정책
- [ ] `CLAUDE.md` - 프로젝트 가이드

### **Step 3️⃣: 저장소 상태 확인 (1분)**

```bash
# 1. 현재 브랜치 확인
git branch -vv
# 예상: * claude/eloquent-meitner-lqxu9r [origin/...]

# 2. 최신 커밋 확인
git log --oneline -3

# 3. 변경사항 확인
git status
# 예상: working tree clean
```

### **Step 4️⃣: 코드 품질 기준 확인 (1분)**

**반드시 준수할 기준**:
- ✅ 함수 최대 50줄 (복잡한 로직 100줄)
- ✅ 100% 타입 힌트
- ✅ 단일 책임 원칙 (SRP)
- ✅ 반복 코드 제거 (DRY - 3줄 이상)
- ✅ 최소 주석 (WHY만, WHAT 아님)

---

## 📋 **작업 시작 전 확인사항**

### ✅ 경로 설정
```bash
# Windows
E:\avm_project  또는 확인된 드라이브

# Linux
/home/user/-/avm_project
```

### ✅ Git 상태
```bash
git status
# 예상: On branch claude/eloquent-meitner-lqxu9r
#       working tree clean
```

### ✅ 의존성
```bash
# 설치 확인
pip list | grep -E "pytest|pandas|numpy"

# 필요시 설치
pip install -r avm_project/requirements.txt
```

### ✅ 파일 접근
```bash
# 프로젝트 구조 확인
ls avm_project/scripts/
ls avm_project/tests/
ls avm_project/docs/
```

---

## 🚨 **문제 해결**

### **❌ 드라이브 오류 (Windows)**

**증상**: `파일을 찾을 수 없음` 또는 `D드라이브 응답 없음`

**해결**:
```powershell
# 1. 자동 수정
.\.claude\fix_external_drive.ps1 -AutoFix

# 2. 수동 확인
Get-PSDrive -PSProvider FileSystem  # 드라이브 확인
Test-Path E:\avm_project           # 경로 확인
```

### **❌ Git 오류**

**증상**: `git status 실패` 또는 `branch 오류`

**해결**:
```bash
# 1. Git 상태 확인
git status

# 2. 원격 저장소 확인
git remote -v
# 예상: origin  http://127.0.0.1:41729/git/Eugene-Eungkwon-Kim/-

# 3. 브랜치 확인
git branch -vv
# 예상: * claude/eloquent-meitner-lqxu9r [origin/claude/eloquent-meitner-lqxu9r]
```

### **❌ 권한 오류**

**증상**: `Permission Denied` 또는 `읽기 전용`

**해결 (Linux)**:
```bash
chmod -R 755 avm_project/
chmod -R u+w avm_project/
```

**해결 (Windows)**:
```
우클릭 → 속성 → 보안 → 편집 → 전체 제어 ✓
```

---

## 📊 **체크리스트 확인**

모든 항목이 ✅ 되어야 작업 시작 가능:

### **환경**
- [ ] 드라이브 경로 확인됨
- [ ] Git 저장소 접근 가능
- [ ] 파일 읽기/쓰기 권한 있음
- [ ] 필요한 패키지 설치됨

### **지식**
- [ ] ENVIRONMENT_SETUP_GUIDE.md 읽음
- [ ] EXECUTION_POLICY.md 읽음
- [ ] CLAUDE.md 읽음
- [ ] 코드 품질 기준 이해함

### **상태**
- [ ] Git 상태: working tree clean
- [ ] 브랜치: claude/eloquent-meitner-lqxu9r
- [ ] 최신 커밋 확인함
- [ ] 파일 구조 확인함

---

## 🎯 **첫 작업 수행**

모든 체크 완료 후, 다음 명령어로 첫 작업 시작:

```bash
# 1. 테스트 실행
python avm_project/scripts/test_full_pipeline.py

# 2. 최근 커밋 확인
git log --oneline -5

# 3. 프로젝트 상태 확인
python -c "
import sys
sys.path.insert(0, 'avm_project')
print('✅ 프로젝트 구조 확인됨')
"
```

---

## 📞 **문제 발생 시**

1. **이 체크리스트의 "문제 해결" 섹션 확인**
2. **`.claude/ENVIRONMENT_SETUP_GUIDE.md` 참조**
3. **Git 히스토리 확인**: `git log --all --oneline -20`
4. **다른 에이전트 작업 확인**: `git show HEAD`
5. **여전히 해결 안 되면**: GitHub Issues 작성 또는 팀에 보고

---

## ⏱️ **소요 시간**

- 체크리스트: **5분**
- 문제 해결: **5-10분**
- 작업 시작: **10-15분**

**총 준비 시간: 20분 이내**

---

## ✨ **준비 완료 신호**

```
✅ 환경 설정 완료
✅ Git 상태 정상
✅ 파일 접근 가능
✅ 정책 문서 이해함
✅ 코드 기준 숙지함

→ 작업 시작 가능! 🚀
```

---

**버전**: 1.0.0  
**마지막 업데이트**: 2026-06-26  
**담당**: 모든 Claude 에이전트
