# GitHub 업로드 가이드

## 1단계: Git 설치

Git이 설치되어 있지 않습니다. 다음 방법 중 하나를 선택하세요:

### 방법 1: Git 공식 웹사이트에서 설치
1. https://git-scm.com/download/win 접속
2. Windows용 Git 다운로드 및 설치
3. 설치 후 터미널 재시작

### 방법 2: winget 사용 (Windows 10/11)
```powershell
winget install --id Git.Git -e --source winget
```

## 2단계: Git 설정 (설치 후)

터미널에서 다음 명령어 실행:

```bash
# 사용자 정보 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Git 저장소 초기화
cd C:\Users\USER\OneDrive\Desktop\streamlit
git init

# 파일 추가
git add .

# 첫 커밋
git commit -m "Initial commit: 글로벌 투자 대시보드"
```

## 3단계: GitHub에 업로드

### GitHub에서 새 저장소 생성
1. https://github.com 접속 및 로그인
2. 우측 상단 '+' 클릭 → 'New repository' 선택
3. 저장소 이름 입력 (예: investment-dashboard)
4. Public 또는 Private 선택
5. 'Create repository' 클릭

### 로컬 저장소와 연결
```bash
# GitHub 저장소 URL로 변경
git remote add origin https://github.com/YOUR_USERNAME/investment-dashboard.git

# 기본 브랜치를 main으로 설정
git branch -M main

# GitHub에 푸시
git push -u origin main
```

## 4단계: 이후 변경사항 업데이트

```bash
# 변경된 파일 확인
git status

# 모든 변경사항 추가
git add .

# 커밋 메시지와 함께 커밋
git commit -m "Update: 변경 내용 설명"

# GitHub에 푸시
git push
```

## 주의사항

- `.gitignore` 파일이 이미 생성되어 있어 `.venv` 폴더는 업로드되지 않습니다
- `requirements.txt`를 통해 다른 사람도 동일한 환경을 구성할 수 있습니다
- 민감한 정보(API 키 등)가 있다면 `.env` 파일에 저장하고 `.gitignore`에 추가하세요

## 파일 구조

```
investment-dashboard/
├── app.py                 # 메인 애플리케이션
├── requirements.txt       # Python 패키지 목록
├── README.md             # 프로젝트 설명
├── .gitignore           # Git 제외 파일 목록
└── GITHUB_GUIDE.md      # 이 가이드 파일
```

## 문제 해결

### SSL 인증서 오류
프록시 환경에서는 Git 명령어에 SSL 검증 비활성화가 필요할 수 있습니다:
```bash
git config --global http.sslVerify false
```

### 인증 문제
GitHub에서 Personal Access Token 생성:
1. GitHub 설정 → Developer settings → Personal access tokens
2. Generate new token (classic)
3. repo 권한 체크
4. 생성된 토큰을 비밀번호 대신 사용
