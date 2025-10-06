# 📈 글로벌 투자 기회 포착 대시보드

실시간 글로벌 금융 시장 데이터를 분석하여 투자 기회를 포착하는 Streamlit 기반 대시보드입니다.

## ✨ 주요 기능

### 📊 전체 개요 모드
- 주가지수, 채권, 상품, 암호화폐 등 모든 자산을 한 눈에 확인
- 각 자산의 현재가, 등락률, 미니 차트 표시
- 볼린저밴드와 후행스팬 관계 분석
- 기술적 분석 요약 (RSI, MACD, 이평선)

### 🔍 상세 분석 모드
- 개별 자산의 심층 분석
- 인터랙티브 차트 (Plotly 기반)
- 다양한 기술적 지표:
  - **이동평균선**: MA20, MA50, MA200
  - **볼린저 밴드**: 기간 18, 승수 2.0
  - **RSI**: 기간 14, Signal 6
  - **Stochastic Slow**: 기간 10, %K 6, %D 6
  - **MACD**: 단기 12, 장기 26, Signal 9
  - **일목균형표**: 전환선, 기준선, 선행스팬, 후행스팬, 구름대

## 📦 지원 자산

### 주가지수
- 🇰🇷 KOSPI
- 🇺🇸 S&P 500, 나스닥, 다우존스
- 🇨🇳 상해종합
- 🇯🇵 닛케이225
- 🇩🇪 DAX
- 🇬🇧 FTSE 100

### 채권
- 미국 10년/2년/30년 국채

### 상품
- 금, 은, WTI 원유, 천연가스, 구리

### 암호화폐
- 비트코인, 이더리움

## 🚀 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/YOUR_USERNAME/investment-dashboard.git
cd investment-dashboard
```

### 2. 가상환경 생성 및 활성화
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 앱 실행
```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속하세요.

## 📋 요구사항

- Python 3.8 이상
- 인터넷 연결 (실시간 데이터 수집)

## 🛠️ 기술 스택

- **Streamlit**: 웹 대시보드 프레임워크
- **yfinance**: Yahoo Finance API를 통한 금융 데이터 수집
- **Plotly**: 인터랙티브 차트 생성
- **pandas**: 데이터 처리
- **ta (Technical Analysis)**: 기술적 지표 계산

## 🎨 특징

- ✅ 한국식 차트 색상 (상승: 빨강, 하락: 파랑)
- ✅ 실시간 데이터 자동 업데이트 (5분 캐시)
- ✅ 반응형 레이아웃
- ✅ 다양한 조회 기간 선택 (1개월 ~ 5년)
- ✅ SSL 인증서 문제 자동 해결

## ⚠️ 면책 조항

이 대시보드는 정보 제공 목적으로만 사용됩니다. 투자 결정은 본인의 책임이며, 이 도구는 투자 조언이 아닙니다.

## 📄 라이선스

MIT License

## 👨‍💻 개발자

데이터 출처: Yahoo Finance
