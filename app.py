import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import ta
import ssl
import certifi
from pykrx import stock

# SSL 인증서 문제 해결
ssl._create_default_https_context = ssl._create_unverified_context

# 페이지 설정
st.set_page_config(
    page_title="글로벌 투자 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 자산 정의
ASSETS = {
    "주가지수": {
        "🇰🇷 KOSPI": "^KS11",
        "🇺🇸 S&P 500": "^GSPC",
        "🇺🇸 나스닥": "^IXIC",
        "🇺🇸 다우존스": "^DJI",
        "🇨🇳 상해종합": "000001.SS",
        "🇯🇵 닛케이225": "^N225",
        "🇩🇪 DAX": "^GDAXI",
        "🇬🇧 FTSE 100": "^FTSE",
    },
    "채권": {
        "미국 10년 국채": "^TNX",
        "미국 2년 국채": "^IRX",
        "미국 30년 국채": "^TYX",
    },
    "상품": {
        "금 (Gold)": "GC=F",
        "은 (Silver)": "SI=F",
        "WTI 원유": "CL=F",
        "천연가스": "NG=F",
        "구리": "HG=F",
    },
    "암호화폐": {
        "비트코인": "BTC-USD",
        "이더리움": "ETH-USD",
    }
}

# 캐시를 사용한 데이터 로딩
@st.cache_data(ttl=300)  # 5분 캐시
def load_data(ticker, period="1y"):
    """
    티커 데이터 로드
    """
    try:
        # SSL 검증 비활성화하여 데이터 다운로드
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            return None
        
        # Multi-level columns을 flat하게 변환
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        return data
    except Exception as e:
        st.error(f"데이터 로드 실패: {ticker} - {str(e)}")
        return None

def calculate_indicators(data):
    """
    기술적 지표 계산
    """
    df = data.copy()
    
    # Close 컬럼이 Series인지 확인하고 변환
    close_series = df['Close'].squeeze() if hasattr(df['Close'], 'squeeze') else df['Close']
    
    # 이동평균선
    df['MA20'] = close_series.rolling(window=20).mean()
    df['MA50'] = close_series.rolling(window=50).mean()
    df['MA200'] = close_series.rolling(window=200).mean()
    
    # RSI (기간 14, Signal 6)
    rsi_indicator = ta.momentum.RSIIndicator(close_series, window=14)
    df['RSI'] = rsi_indicator.rsi()
    df['RSI_Signal'] = df['RSI'].rolling(window=6).mean()
    
    # MACD (단기12, 장기26, Signal 9)
    macd = ta.trend.MACD(close_series, window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    # 볼린저 밴드 (기간 18, 승수 2.0)
    bollinger = ta.volatility.BollingerBands(close_series, window=18, window_dev=2.0)
    df['BB_Upper'] = bollinger.bollinger_hband()
    df['BB_Middle'] = bollinger.bollinger_mavg()
    df['BB_Lower'] = bollinger.bollinger_lband()
    
    # 스토캐스틱 슬로우 (기간 10, %K 6, %D 6)
    stoch = ta.momentum.StochasticOscillator(
        high=df['High'].squeeze() if hasattr(df['High'], 'squeeze') else df['High'],
        low=df['Low'].squeeze() if hasattr(df['Low'], 'squeeze') else df['Low'],
        close=close_series,
        window=10,
        smooth_window=6
    )
    df['Stoch_K'] = stoch.stoch()
    df['Stoch_D'] = stoch.stoch_signal()
    
    # 일목균형표 (Ichimoku)
    ichimoku = ta.trend.IchimokuIndicator(
        high=df['High'].squeeze() if hasattr(df['High'], 'squeeze') else df['High'],
        low=df['Low'].squeeze() if hasattr(df['Low'], 'squeeze') else df['Low']
    )
    df['Ichimoku_Conversion'] = ichimoku.ichimoku_conversion_line()  # 전환선 (9일)
    df['Ichimoku_Base'] = ichimoku.ichimoku_base_line()  # 기준선 (26일)
    df['Ichimoku_A'] = ichimoku.ichimoku_a()  # 선행스팬A
    df['Ichimoku_B'] = ichimoku.ichimoku_b()  # 선행스팬B
    
    # 후행스팬 계산 (당일 종가를 26일 전에 표시)
    df['Ichimoku_Lagging'] = close_series.shift(-26)
    
    return df

def create_chart(data, title):
    """
    Plotly를 사용한 인터랙티브 차트 생성
    """
    # 서브플롯 생성: 가격, 거래량, RSI, Stochastic, MACD
    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=(f'{title} 가격', '거래량', 'RSI', 'Stochastic Slow', 'MACD'),
        row_heights=[0.4, 0.15, 0.15, 0.15, 0.15]
    )
    
    # 캔들스틱 차트 (상승: 빨강, 하락: 파랑)
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='가격',
            increasing_line_color='red',
            decreasing_line_color='blue',
            increasing_fillcolor='red',
            decreasing_fillcolor='blue'
        ),
        row=1, col=1
    )
    
    # 이동평균선
    fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], name='MA20', line=dict(color='orange', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], name='MA50', line=dict(color='blue', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA200'], name='MA200', line=dict(color='red', width=1)), row=1, col=1)
    
    # 볼린저 밴드
    fig.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], name='BB Upper', line=dict(color='gray', width=1, dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], name='BB Lower', line=dict(color='gray', width=1, dash='dash')), row=1, col=1)
    
    # 일목균형표
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Conversion'], name='전환선(9)', line=dict(color='cyan', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Base'], name='기준선(26)', line=dict(color='magenta', width=1)), row=1, col=1)
    
    # 후행스팬 (26일 뒤로 이동)
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Lagging'], name='후행스팬(26)', line=dict(color='orange', width=1, dash='dot')), row=1, col=1)
    
    # 일목균형표 구름대 - 양운(빨강)과 음운(파랑) 구분
    # 선행스팬A와 B를 비교하여 색상 결정
    for i in range(len(data)):
        if i == 0:
            continue
        
        span_a_curr = data['Ichimoku_A'].iloc[i]
        span_b_curr = data['Ichimoku_B'].iloc[i]
        span_a_prev = data['Ichimoku_A'].iloc[i-1]
        span_b_prev = data['Ichimoku_B'].iloc[i-1]
        
        # 양운 (선행스팬A > 선행스팬B): 빨간색
        if span_a_curr >= span_b_curr:
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_a_prev, span_a_curr],
                fill=None,
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_b_prev, span_b_curr],
                fill='tonexty',
                mode='lines',
                line=dict(width=0),
                fillcolor='rgba(255, 0, 0, 0.2)',
                showlegend=False,
                hoverinfo='skip'
            ), row=1, col=1)
        # 음운 (선행스팬A < 선행스팬B): 파란색
        else:
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_a_prev, span_a_curr],
                fill=None,
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_b_prev, span_b_curr],
                fill='tonexty',
                mode='lines',
                line=dict(width=0),
                fillcolor='rgba(0, 0, 255, 0.2)',
                showlegend=False,
                hoverinfo='skip'
            ), row=1, col=1)
    
    # 선행스팬 라인 표시
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data['Ichimoku_A'], 
        name='선행스팬A', 
        line=dict(color='green', width=1),
        showlegend=True
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data['Ichimoku_B'], 
        name='선행스팬B', 
        line=dict(color='red', width=1),
        showlegend=True
    ), row=1, col=1)
    
    # 거래량 (상승: 빨강, 하락: 파랑)
    colors = ['red' if close >= open_ else 'blue' for close, open_ in zip(data['Close'], data['Open'])]
    fig.add_trace(
        go.Bar(x=data.index, y=data['Volume'], name='거래량', marker_color=colors),
        row=2, col=1
    )
    
    # RSI
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name='RSI', line=dict(color='purple', width=2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI_Signal'], name='RSI Signal', line=dict(color='orange', width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    # Stochastic Slow
    fig.add_trace(go.Scatter(x=data.index, y=data['Stoch_K'], name='%K (6)', line=dict(color='blue', width=2)), row=4, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stoch_D'], name='%D (6)', line=dict(color='red', width=2)), row=4, col=1)
    fig.add_hline(y=80, line_dash="dash", line_color="red", row=4, col=1)
    fig.add_hline(y=20, line_dash="dash", line_color="green", row=4, col=1)
    
    # MACD
    fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD', line=dict(color='blue', width=2)), row=5, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MACD_Signal'], name='Signal', line=dict(color='red', width=2)), row=5, col=1)
    fig.add_trace(go.Bar(x=data.index, y=data['MACD_Hist'], name='Histogram', marker_color='gray'), row=5, col=1)
    
    # 레이아웃 업데이트
    fig.update_layout(
        height=1200,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig

def create_simple_chart(data, title):
    """
    가격 차트만 있는 간단한 차트 생성 (보조지표 제외)
    """
    fig = go.Figure()
    
    # 캔들스틱 차트 (상승: 빨강, 하락: 파랑)
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='가격',
            increasing_line_color='red',
            decreasing_line_color='blue',
            increasing_fillcolor='red',
            decreasing_fillcolor='blue'
        )
    )
    
    # 이동평균선
    fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], name='MA20', line=dict(color='orange', width=1)))
    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], name='MA50', line=dict(color='blue', width=1)))
    fig.add_trace(go.Scatter(x=data.index, y=data['MA200'], name='MA200', line=dict(color='red', width=1)))
    
    # 볼린저 밴드
    fig.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], name='BB Upper', line=dict(color='gray', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], name='BB Lower', line=dict(color='gray', width=1, dash='dash')))
    
    # 일목균형표
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Conversion'], name='전환선(9)', line=dict(color='cyan', width=1)))
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Base'], name='기준선(26)', line=dict(color='magenta', width=1)))
    
    # 후행스팬 (26일 뒤로 이동)
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Lagging'], name='후행스팬(26)', line=dict(color='orange', width=1, dash='dot')))
    
    # 일목균형표 구름대 - 양운(빨강)과 음운(파랑) 구분
    for i in range(len(data)):
        if i == 0:
            continue
        
        span_a_curr = data['Ichimoku_A'].iloc[i]
        span_b_curr = data['Ichimoku_B'].iloc[i]
        span_a_prev = data['Ichimoku_A'].iloc[i-1]
        span_b_prev = data['Ichimoku_B'].iloc[i-1]
        
        # 양운 (선행스팬A > 선행스팬B): 빨간색
        if span_a_curr >= span_b_curr:
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_a_prev, span_a_curr],
                fill=None,
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_b_prev, span_b_curr],
                fill='tonexty',
                mode='lines',
                line=dict(width=0),
                fillcolor='rgba(255, 0, 0, 0.2)',
                showlegend=False,
                hoverinfo='skip'
            ))
        # 음운 (선행스팬A < 선행스팬B): 파란색
        else:
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_a_prev, span_a_curr],
                fill=None,
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            fig.add_trace(go.Scatter(
                x=[data.index[i-1], data.index[i]],
                y=[span_b_prev, span_b_curr],
                fill='tonexty',
                mode='lines',
                line=dict(width=0),
                fillcolor='rgba(0, 0, 255, 0.2)',
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # 선행스팬 라인 표시
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data['Ichimoku_A'], 
        name='선행스팬A', 
        line=dict(color='green', width=1),
        showlegend=True
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data['Ichimoku_B'], 
        name='선행스팬B', 
        line=dict(color='red', width=1),
        showlegend=True
    ))
    
    # 레이아웃 업데이트
    fig.update_layout(
        title=title,
        height=600,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig

def create_mini_chart(data, title):
    """
    미니 차트 생성 (종목 스크리닝용)
    """
    mini_fig = go.Figure()
    mini_fig.add_trace(go.Candlestick(
        x=data.index[-60:],
        open=data['Open'][-60:],
        high=data['High'][-60:],
        low=data['Low'][-60:],
        close=data['Close'][-60:],
        increasing_line_color='red',
        decreasing_line_color='blue',
        increasing_fillcolor='red',
        decreasing_fillcolor='blue',
        showlegend=False,
        name='가격'
    ))
    
    # 이동평균선 추가
    mini_fig.add_trace(go.Scatter(
        x=data.index[-60:],
        y=data['MA20'][-60:],
        name='MA20',
        line=dict(color='orange', width=1)
    ))
    
    # 볼린저밴드 추가
    mini_fig.add_trace(go.Scatter(
        x=data.index[-60:],
        y=data['BB_Upper'][-60:],
        name='BB상단',
        line=dict(color='gray', width=1, dash='dash'),
        showlegend=False
    ))
    
    mini_fig.add_trace(go.Scatter(
        x=data.index[-60:],
        y=data['BB_Lower'][-60:],
        name='BB하단',
        line=dict(color='gray', width=1, dash='dash'),
        fill='tonexty',
        fillcolor='rgba(128, 128, 128, 0.1)',
        showlegend=False
    ))
    
    # 후행스팬 추가
    mini_fig.add_trace(go.Scatter(
        x=data.index[-60:],
        y=data['Ichimoku_Lagging'][-60:],
        name='후행스팬',
        line=dict(color='orange', width=2, dash='dot')
    ))
    
    mini_fig.update_layout(
        title=title,
        height=250,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=8)
        ),
        xaxis=dict(showticklabels=False),
        yaxis=dict(side='right')
    )
    
    return mini_fig

def screen_kospi_stocks():
    """
    KOSPI 우량기업 스크리닝
    대상: KOSPI 200 지수 편입 종목 (시가총액 상위 200개 대형주)
    조건: 20일 신고가 종목만 빠르게 필터링 후 차트로 확인
    """
    
    try:
        # KOSPI 200 종목 리스트 가져오기 (우량 대형주만)
        today = datetime.now().strftime("%Y%m%d")
        
        # KOSPI 200 지수 구성 종목 가져오기
        try:
            kospi200_tickers = stock.get_index_portfolio_deposit_file("1028")  # KOSPI 200 코드
            st.info(f"📊 KOSPI 200 우량기업 {len(kospi200_tickers)}개 종목에서 20일 신고가 종목 검색 중...")
        except:
            # 실패 시 시가총액 상위 종목으로 대체
            all_tickers = stock.get_market_ticker_list(today, market="KOSPI")
            # 시가총액 기준으로 상위 200개 선택
            market_caps = {}
            for ticker in all_tickers[:300]:  # 상위 300개만 체크
                try:
                    cap = stock.get_market_cap(today, today, ticker)
                    if not cap.empty:
                        market_caps[ticker] = cap['시가총액'].iloc[-1]
                except:
                    continue
            
            # 시가총액 상위 200개 선택
            sorted_tickers = sorted(market_caps.items(), key=lambda x: x[1], reverse=True)
            kospi200_tickers = [t[0] for t in sorted_tickers[:200]]
            st.info(f"📊 시가총액 상위 {len(kospi200_tickers)}개 우량기업에서 20일 신고가 종목 검색 중...")
        
        # 종목명 가져오기
        kospi_symbols = {}
        for ticker in kospi200_tickers:
            try:
                name = stock.get_market_ticker_name(ticker)
                # yfinance 형식으로 변환 (6자리 코드.KS)
                kospi_symbols[name] = f"{ticker}.KS"
            except:
                continue
        
    except Exception as e:
        st.warning(f"⚠️ pykrx로 종목 리스트를 가져오는 데 실패했습니다: {str(e)}")
        st.info("💡 주요 우량주만으로 분석을 진행합니다...")
        
        # 실패 시 주요 우량주만 사용 (KOSPI 200 주요 종목)
        kospi_symbols = {
            # IT/반도체 대형주
            "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS",
            "삼성SDI": "006400.KS", "LG전자": "066570.KS", "삼성전기": "009150.KS",
            "SK스퀘어": "402340.KS", "NAVER": "035420.KS", "카카오": "035720.KS",
            # 바이오/제약 대형주
            "삼성바이오로직스": "207940.KS", "셀트리온": "068270.KS", "셀트리온헬스케어": "091990.KS",
            # 자동차 대형주
            "현대차": "005380.KS", "기아": "000270.KS", "현대모비스": "012330.KS",
            # 화학/소재 대형주
            "LG화학": "051910.KS", "포스코홀딩스": "005490.KS", "SK이노베이션": "096770.KS",
            "POSCO DX": "022100.KS", "롯데케미칼": "011170.KS",
            # 금융 대형주
            "KB금융": "105560.KS", "신한지주": "055550.KS", "하나금융지주": "086790.KS",
            "우리금융지주": "316140.KS", "삼성생명": "032830.KS", "삼성화재": "000810.KS",
            # 건설/중공업 대형주
            "삼성물산": "028260.KS", "현대건설": "000720.KS", "HD현대": "267250.KS",
            # 유통/서비스 대형주
            "신세계": "004170.KS", "롯데쇼핑": "023530.KS", "CJ제일제당": "097950.KS",
        }
    
    new_high_stocks = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(kospi_symbols)
    processed = 0
    errors = 0
    
    # 1단계: 20일 신고가 종목만 빠르게 필터링 (지표 계산 없이)
    for idx, (name, symbol) in enumerate(kospi_symbols.items()):
        try:
            status_text.text(f"검색 중: {name} ({idx+1}/{total}) | 20일 신고가: {len(new_high_stocks)}개 | 오류: {errors}개")
            progress_bar.progress((idx + 1) / total)
            
            # 최소한의 데이터만 로드 (1개월)
            data = load_data(symbol, period="1mo")
            if data is None or data.empty or len(data) < 20:
                errors += 1
                continue
            
            latest = data.iloc[-1]
            
            # 20일 신고가 체크 (지표 계산 없이 단순 비교만)
            high_20d = data['High'][-20:].max()
            is_new_high = latest['Close'] >= high_20d * 0.99  # 99% 이상이면 신고가 근처
            
            if is_new_high:
                # 신고가 종목 발견 시 3개월 데이터로 지표 계산
                data_3m = load_data(symbol, period="3mo")
                if data_3m is not None and not data_3m.empty:
                    data_with_indicators = calculate_indicators(data_3m)
                    latest_with_indicators = data_with_indicators.iloc[-1]
                    new_high_stocks.append((name, symbol, data_with_indicators, latest_with_indicators))
            
            processed += 1
        
        except Exception as e:
            errors += 1
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    # 등락률 높은 순으로 정렬 (모멘텀 강한 종목 우선)
    new_high_stocks.sort(key=lambda x: ((x[3]['Close'] - x[2].iloc[-2]['Close']) / x[2].iloc[-2]['Close']) * 100, reverse=True)
    
    st.success(f"✅ 분석 완료: 총 {processed}개 종목 처리, {len(new_high_stocks)}개 종목이 20일 신고가 달성")
    
    return new_high_stocks

def display_metrics(data, name):
    """
    주요 지표 표시
    """
    latest = data.iloc[-1]
    previous = data.iloc[-2]
    
    current_price = latest['Close']
    price_change = current_price - previous['Close']
    price_change_pct = (price_change / previous['Close']) * 100
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="현재가",
            value=f"{current_price:,.2f}",
            delta=f"{price_change_pct:+.2f}%"
        )
    
    with col2:
        rsi_value = latest['RSI']
        rsi_status = "과매수" if rsi_value > 70 else "과매도" if rsi_value < 30 else "중립"
        st.metric(
            label=f"RSI ({rsi_status})",
            value=f"{rsi_value:.2f}"
        )

# ==================== 메인 앱 ====================

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 뷰 모드 선택
    view_mode = st.radio(
        "보기 모드",
        ["📊 전체 개요", "🔍 상세 분석"],
        index=0
    )
    
    if view_mode == "🔍 상세 분석":
        # 카테고리 선택
        selected_category = st.selectbox(
            "자산 카테고리",
            list(ASSETS.keys())
        )
        
        # 자산 선택
        selected_asset = st.selectbox(
            "자산 선택",
            list(ASSETS[selected_category].keys())
        )
    
    # 기간 선택
    period_options = {
        "1개월": "1mo",
        "3개월": "3mo",
        "6개월": "6mo",
        "1년": "1y",
        "2년": "2y",
        "5년": "5y"
    }
    selected_period = st.selectbox(
        "조회 기간",
        list(period_options.keys()),
        index=3
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ 보조지표 설정")
    
    with st.expander("📊 지표 설정값 보기", expanded=False):
        st.markdown("""
        **이동평균선 (MA)**
        - MA20: 20일
        - MA50: 50일
        - MA200: 200일
        
        **볼린저 밴드 (BB)**
        - 기간: 18
        - 승수: 2.00
        
        **RSI**
        - 기간: 14
        - Signal: 6
        
        **Stochastic Slow**
        - 기간: 10
        - %K: 6
        - %D: 6
        
        **MACD**
        - 단기: 12
        - 장기: 26
        - Signal: 9
        
        **일목균형표**
        - 전환선: 9일
        - 기준선: 26일
        - 선행스팬: 52일
        - 후행스팬: 26일
        """)

# ==================== 전체 개요 모드 ====================
if view_mode == "📊 전체 개요":
    
    # 각 카테고리별로 데이터 표시
    for category_name, category_assets in ASSETS.items():
        st.subheader(f"📌 {category_name}")
        
        # 카테고리별 컬럼 수 결정
        num_cols = min(4, len(category_assets))
        cols = st.columns(num_cols)
        
        for idx, (asset_name, ticker) in enumerate(category_assets.items()):
            with cols[idx % num_cols]:
                with st.spinner(f'{asset_name} 로딩...'):
                    data = load_data(ticker, period=period_options[selected_period])
                    
                    if data is not None and not data.empty:
                        latest = data.iloc[-1]
                        previous = data.iloc[-2]
                        
                        current_price = latest['Close']
                        price_change = current_price - previous['Close']
                        price_change_pct = (price_change / previous['Close']) * 100
                        
                        # 카드 형태로 표시
                        st.markdown(f"### {asset_name}")
                        st.metric(
                            label="현재가",
                            value=f"{current_price:,.2f}",
                            delta=f"{price_change_pct:+.2f}%"
                        )
                        
                        # 간단한 차트
                        data_with_indicators = calculate_indicators(data)
                        
                        # 미니 차트 생성
                        mini_fig = go.Figure()
                        mini_fig.add_trace(go.Candlestick(
                            x=data.index[-60:],  # 최근 60일 (후행스팬 표시 위해)
                            open=data['Open'][-60:],
                            high=data['High'][-60:],
                            low=data['Low'][-60:],
                            close=data['Close'][-60:],
                            increasing_line_color='red',
                            decreasing_line_color='blue',
                            increasing_fillcolor='red',
                            decreasing_fillcolor='blue',
                            showlegend=False,
                            name='가격'
                        ))
                        
                        # 이동평균선 추가
                        mini_fig.add_trace(go.Scatter(
                            x=data.index[-60:],
                            y=data_with_indicators['MA20'][-60:],
                            name='MA20',
                            line=dict(color='orange', width=1)
                        ))
                        
                        # 볼린저밴드 추가
                        mini_fig.add_trace(go.Scatter(
                            x=data.index[-60:],
                            y=data_with_indicators['BB_Upper'][-60:],
                            name='BB상단',
                            line=dict(color='gray', width=1, dash='dash'),
                            showlegend=False
                        ))
                        
                        mini_fig.add_trace(go.Scatter(
                            x=data.index[-60:],
                            y=data_with_indicators['BB_Lower'][-60:],
                            name='BB하단',
                            line=dict(color='gray', width=1, dash='dash'),
                            fill='tonexty',
                            fillcolor='rgba(128, 128, 128, 0.1)',
                            showlegend=False
                        ))
                        
                        # 후행스팬 추가 (주황색 점선)
                        mini_fig.add_trace(go.Scatter(
                            x=data.index[-60:],
                            y=data_with_indicators['Ichimoku_Lagging'][-60:],
                            name='후행스팬',
                            line=dict(color='orange', width=2, dash='dot')
                        ))
                        
                        mini_fig.update_layout(
                            height=250,
                            margin=dict(l=0, r=0, t=0, b=0),
                            xaxis_rangeslider_visible=False,
                            showlegend=True,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1,
                                font=dict(size=8)
                            ),
                            xaxis=dict(showticklabels=False),
                            yaxis=dict(side='right')
                        )
                        
                        st.plotly_chart(mini_fig, use_container_width=True)
                        
                        # 기술적 분석 요약
                        with st.expander("📊 기술적 분석 요약"):
                            latest_ind = data_with_indicators.iloc[-1]
                            
                            # 볼린저밴드와 후행스팬 분석
                            lagging_span = latest_ind['Ichimoku_Lagging']
                            bb_upper = latest_ind['BB_Upper']
                            bb_lower = latest_ind['BB_Lower']
                            
                            # 후행스팬과 볼린저밴드 관계
                            if pd.notna(lagging_span):
                                if lagging_span > bb_upper:
                                    st.write("🔴 후행스팬 > BB상단 (과매수)")
                                elif lagging_span < bb_lower:
                                    st.write("🟢 후행스팬 < BB하단 (과매도)")
                                elif lagging_span > current_price:
                                    st.write("🟢 후행스팬 > 현재가 (강세)")
                                elif lagging_span < current_price:
                                    st.write("🔴 후행스팬 < 현재가 (약세)")
                                else:
                                    st.write("🟡 후행스팬 = 현재가")
                            
                            st.markdown("---")
                            
                            # RSI
                            rsi = latest_ind['RSI']
                            if rsi > 70:
                                st.write("🔴 RSI: 과매수")
                            elif rsi < 30:
                                st.write("🟢 RSI: 과매도")
                            else:
                                st.write(f"🟡 RSI: {rsi:.1f}")
                            
                            # MACD
                            if latest_ind['MACD'] > latest_ind['MACD_Signal']:
                                st.write("🟢 MACD: 상승")
                            else:
                                st.write("🔴 MACD: 하락")
                            
                            # 이동평균
                            if current_price > latest_ind['MA20']:
                                st.write("✅ MA20 위")
                            else:
                                st.write("❌ MA20 아래")
                    else:
                        st.error(f"❌ {asset_name} 데이터 로드 실패")
        
        st.markdown("---")

# ==================== 상세 분석 모드 ====================
elif view_mode == "🔍 상세 분석":
    # 티커 가져오기
    ticker = ASSETS[selected_category][selected_asset]

    # 데이터 로드
    with st.spinner(f'{selected_asset} 데이터 로딩 중...'):
        data = load_data(ticker, period=period_options[selected_period])

    if data is not None and not data.empty:
        # 지표 계산
        data_with_indicators = calculate_indicators(data)
        
        # 주요 지표 표시
        st.subheader(f"📊 {selected_asset} 현황")
        display_metrics(data_with_indicators, selected_asset)
        
        st.markdown("---")
        
        # 간단한 가격 차트만 표시
        st.subheader(f"📈 {selected_asset} 가격 차트")
        simple_chart = create_simple_chart(data_with_indicators, selected_asset)
        st.plotly_chart(simple_chart, use_container_width=True)
        
        # KOSPI 선택 시 종목 스크리닝 결과 표시
        if selected_asset == "🇰🇷 KOSPI":
            st.markdown("---")
            st.subheader("🔍 KOSPI 우량기업 스크리닝")
            
            with st.spinner("KOSPI 200 우량기업에서 20일 신고가 종목 검색 중... (약 1분 소요)"):
                new_high_stocks = screen_kospi_stocks()
            
            # 20일 신고가 종목 표시
            st.info("📊 대상: KOSPI 200 우량기업 (시가총액 상위 200개) | 조건: 20일 신고가")
            
            if new_high_stocks:
                st.success(f"✅ {len(new_high_stocks)}개 종목이 20일 신고가를 달성했습니다!")
                
                # 3열로 표시
                num_cols = 3
                for i in range(0, len(new_high_stocks), num_cols):
                    cols = st.columns(num_cols)
                    for j in range(num_cols):
                        idx = i + j
                        if idx < len(new_high_stocks):
                            name, symbol, stock_data, latest_data = new_high_stocks[idx]
                            
                            with cols[j]:
                                st.markdown(f"### {name}")
                                
                                # 현재가 및 등락률
                                if len(stock_data) >= 2:
                                    prev = stock_data.iloc[-2]
                                    change_pct = ((latest_data['Close'] - prev['Close']) / prev['Close']) * 100
                                    st.metric("현재가", f"{latest_data['Close']:,.0f}원", f"{change_pct:+.2f}%")
                                else:
                                    st.metric("현재가", f"{latest_data['Close']:,.0f}원")
                                
                                # 기술적 지표 표시
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    rsi = latest_data['RSI']
                                    if pd.notna(rsi):
                                        st.metric("RSI", f"{rsi:.1f}")
                                with col2:
                                    # 후행스팬과 BB상단 비교
                                    if pd.notna(latest_data['Ichimoku_Lagging']) and pd.notna(latest_data['BB_Upper']):
                                        lagging = latest_data['Ichimoku_Lagging']
                                        bb_upper = latest_data['BB_Upper']
                                        breakthrough = "✅" if lagging > bb_upper else "❌"
                                        st.metric("후행>BB", breakthrough)
                                with col3:
                                    # 20일 신고가 달성률
                                    high_20d = stock_data['High'][-20:].max()
                                    achievement = (latest_data['Close'] / high_20d) * 100
                                    st.metric("신고가", f"{achievement:.1f}%")
                                
                                # 상세 차트 (후행스팬, 볼린저밴드 포함)
                                chart = create_simple_chart(stock_data, name)
                                st.plotly_chart(chart, use_container_width=True)
                                
                                st.markdown("---")
            else:
                st.warning("⚠️ 현재 20일 신고가를 달성한 종목이 없습니다.")
                st.info("💡 팁: 시장 조정 시기에는 신고가 종목이 적을 수 있습니다.")


    else:
        st.error(f"❌ {selected_asset} 데이터를 불러올 수 없습니다. 다른 자산을 선택해주세요.")

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>📊 데이터 출처: Yahoo Finance | ⚠️ 투자 결정은 본인의 책임입니다.</p>
    <p>이 대시보드는 정보 제공 목적이며, 투자 조언이 아닙니다.</p>
</div>
""", unsafe_allow_html=True)
