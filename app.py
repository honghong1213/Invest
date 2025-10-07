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

def display_metrics(data, name):
    """
    주요 지표 표시
    """
    latest = data.iloc[-1]
    previous = data.iloc[-2]
    
    current_price = latest['Close']
    price_change = current_price - previous['Close']
    price_change_pct = (price_change / previous['Close']) * 100
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="현재가",
            value=f"{current_price:,.2f}",
            delta=f"{price_change_pct:+.2f}%"
        )
    
    with col2:
        st.metric(
            label="거래량",
            value=f"{latest['Volume']:,.0f}"
        )
    
    with col3:
        rsi_value = latest['RSI']
        rsi_status = "과매수" if rsi_value > 70 else "과매도" if rsi_value < 30 else "중립"
        st.metric(
            label=f"RSI ({rsi_status})",
            value=f"{rsi_value:.2f}"
        )
    
    with col4:
        st.metric(
            label="52주 최고",
            value=f"{data['High'].tail(252).max():,.2f}"
        )
    
    with col5:
        st.metric(
            label="52주 최저",
            value=f"{data['Low'].tail(252).min():,.2f}"
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
        
        # 차트 표시
        st.subheader(f"📈 {selected_asset} 차트 분석")
        chart = create_chart(data_with_indicators, selected_asset)
        st.plotly_chart(chart, use_container_width=True)
        
        # 추가 분석 정보
        st.markdown("---")
        st.subheader("🔍 기술적 분석 요약")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 이동평균선 분석")
            latest = data_with_indicators.iloc[-1]
            current_price = latest['Close']
            
            ma_analysis = []
            if current_price > latest['MA20']:
                ma_analysis.append("✅ 20일 이평선 위")
            else:
                ma_analysis.append("❌ 20일 이평선 아래")
                
            if current_price > latest['MA50']:
                ma_analysis.append("✅ 50일 이평선 위")
            else:
                ma_analysis.append("❌ 50일 이평선 아래")
                
            if current_price > latest['MA200']:
                ma_analysis.append("✅ 200일 이평선 위")
            else:
                ma_analysis.append("❌ 200일 이평선 아래")
            
            for analysis in ma_analysis:
                st.write(analysis)
            
            st.markdown("#### 일목균형표 분석")
            # 일목균형표 신호
            if current_price > latest['Ichimoku_Base']:
                st.write("✅ 기준선(26) 위")
            else:
                st.write("❌ 기준선(26) 아래")
            
            if latest['Ichimoku_Conversion'] > latest['Ichimoku_Base']:
                st.write("🟢 전환선 > 기준선 (상승)")
            else:
                st.write("🔴 전환선 < 기준선 (하락)")
            
            if latest['Ichimoku_A'] > latest['Ichimoku_B']:
                st.write("🟢 구름대: 양운 (상승)")
            else:
                st.write("🔴 구름대: 음운 (하락)")
        
        with col2:
            st.markdown("#### 보조지표 신호")
            
            # RSI 신호
            rsi = latest['RSI']
            if rsi > 70:
                st.write("🔴 RSI 과매수 구간 (매도 고려)")
            elif rsi < 30:
                st.write("🟢 RSI 과매도 구간 (매수 고려)")
            else:
                st.write("🟡 RSI 중립 구간")
            
            # Stochastic 신호
            stoch_k = latest['Stoch_K']
            stoch_d = latest['Stoch_D']
            if stoch_k > 80 and stoch_d > 80:
                st.write("🔴 Stochastic 과매수 구간")
            elif stoch_k < 20 and stoch_d < 20:
                st.write("🟢 Stochastic 과매도 구간")
            else:
                if stoch_k > stoch_d:
                    st.write("🟢 Stochastic 상승 크로스")
                else:
                    st.write("🔴 Stochastic 하락 크로스")
            
            # MACD 신호
            if latest['MACD'] > latest['MACD_Signal']:
                st.write("🟢 MACD 상승 시그널")
            else:
                st.write("🔴 MACD 하락 시그널")
            
            # 볼린저 밴드
            if current_price > latest['BB_Upper']:
                st.write("🔴 볼린저 밴드 상단 돌파")
            elif current_price < latest['BB_Lower']:
                st.write("🟢 볼린저 밴드 하단 돌파")
            else:
                st.write("🟡 볼린저 밴드 내부")

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
