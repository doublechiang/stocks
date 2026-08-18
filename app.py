import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import timedelta
import yfinance as yf
import time
import init_db

# 確保資料庫與資料表已初始化
init_db.create_tables()

DB_PATH = 'stock_data.db'
START_DATE = '2020-01-01'

def estimate_announcement_date(period_end_str):
    dt = pd.to_datetime(period_end_str)
    if dt.month == 3: return f"{dt.year}-05-15"
    elif dt.month == 6: return f"{dt.year}-08-14"
    elif dt.month == 9: return f"{dt.year}-11-14"
    elif dt.month == 12: return f"{dt.year + 1}-03-31"
    else: return (dt + timedelta(days=45)).strftime('%Y-%m-%d')

def fetch_data_for_stock(stock_id):
    api = DataLoader()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    success = True
    
    try:
        # 1. 抓取 EPS
        fs_df = api.taiwan_stock_financial_statement(stock_id=stock_id, start_date=START_DATE)
        if not fs_df.empty:
            eps_df = fs_df[fs_df['type'] == 'EPS'].copy()
            for _, row in eps_df.iterrows():
                dt = pd.to_datetime(row['date'])
                year = dt.year
                quarter = (dt.month - 1) // 3 + 1
                announce_date = estimate_announcement_date(row['date'])
                cursor.execute('''
                    INSERT OR REPLACE INTO eps_data (stock_id, year, quarter, eps_value, announcement_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (stock_id, year, quarter, row['value'], announce_date))
                
        # 2. 抓取股價
        yf_ticker = f"{stock_id}.TW"
        ticker = yf.Ticker(yf_ticker)
        price_df = ticker.history(start=START_DATE, auto_adjust=False)
        if not price_df.empty:
            for date_idx, row in price_df.iterrows():
                date_str = date_idx.strftime('%Y-%m-%d')
                adj_close = float(row['Adj Close']) if 'Adj Close' in price_df.columns else float(row['Close'])
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_prices (stock_id, date, close_price, volume, adj_close_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (stock_id, date_str, float(row['Close']), int(row['Volume']), adj_close))
        else:
            success = False
            
    except Exception as e:
        st.error(f"下載失敗: {e}")
        success = False
        
    conn.commit()
    conn.close()
    return success

def plot_divergence(stock_id):
    conn = sqlite3.connect(DB_PATH)
    df_price = pd.read_sql_query('SELECT date, adj_close_price as close_price FROM daily_prices WHERE stock_id = ? ORDER BY date ASC', conn, params=(stock_id,))
    df_eps = pd.read_sql_query('SELECT year, quarter, eps_value, announcement_date FROM eps_data WHERE stock_id = ? ORDER BY year ASC, quarter ASC', conn, params=(stock_id,))
    conn.close()
    
    if len(df_eps) < 4 or df_price.empty:
        return None
        
    df_eps['ttm_eps'] = df_eps['eps_value'].rolling(window=4).sum()
    df_eps = df_eps.dropna(subset=['ttm_eps', 'announcement_date']).copy()
    df_eps.reset_index(drop=True, inplace=True)
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df_price['date'], y=df_price['close_price'], name="還原收盤價", line=dict(color='#1f77b4', width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_eps['announcement_date'], y=df_eps['ttm_eps'], name="近四季EPS (TTM)", line=dict(color='#ff7f0e', width=3, shape='hv')), secondary_y=True)
    
    buy_signals_x, buy_signals_y = [], []
    risk_signals_x, risk_signals_y = [], []
    df_eps['prev_ttm_eps'] = df_eps['ttm_eps'].shift(1)
    
    for i in range(1, len(df_eps)):
        current_date = df_eps.loc[i, 'announcement_date']
        prev_date = df_eps.loc[i-1, 'announcement_date']
        
        current_price_df = df_price[df_price['date'] >= current_date]
        prev_price_df = df_price[df_price['date'] >= prev_date]
        
        if current_price_df.empty or prev_price_df.empty: continue
            
        current_price = current_price_df.iloc[0]['close_price']
        prev_price = prev_price_df.iloc[0]['close_price']
        
        eps_trend_up = df_eps.loc[i, 'ttm_eps'] > df_eps.loc[i, 'prev_ttm_eps']
        eps_trend_down = df_eps.loc[i, 'ttm_eps'] < df_eps.loc[i, 'prev_ttm_eps']
        price_trend_down = current_price < prev_price
        price_trend_up = current_price > prev_price
        
        if eps_trend_up and price_trend_down:
            buy_signals_x.append(current_date)
            buy_signals_y.append(current_price)
        elif eps_trend_down and price_trend_up:
            risk_signals_x.append(current_date)
            risk_signals_y.append(current_price)
            
    fig.add_trace(go.Scatter(x=buy_signals_x, y=buy_signals_y, mode='markers', name="🌟 低估背離買點", marker=dict(color='green', size=14, symbol='triangle-up')), secondary_y=False)
    fig.add_trace(go.Scatter(x=risk_signals_x, y=risk_signals_y, mode='markers', name="⚠️ 高估背離風險", marker=dict(color='red', size=14, symbol='triangle-down')), secondary_y=False)
    
    # 取得最新資訊
    last_price = df_price.iloc[-1]['close_price']
    last_ttm = df_eps.iloc[-1]['ttm_eps']
    
    fig.update_layout(
        title_text=f"<b>{stock_id} 股價與 EPS 背離分析圖</b> (最新價格: {last_price:.2f}, 近四季EPS: {last_ttm:.2f})",
        xaxis_title="日期",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600
    )
    return fig

# Streamlit UI
st.set_page_config(page_title="台股背離分析系統", layout="wide", page_icon="📈")
st.title("📈 台股 EPS 與股價背離掃描器")
st.markdown("輸入任何台灣上市櫃股票代號，系統將自動為您繪製 **還原股價** 與 **近四季EPS (TTM)** 的背離分析圖。")

col1, col2 = st.columns([1, 4])
with col1:
    stock_input = st.text_input("🔍 請輸入股票代號 (例如: 2330)", "2330")
    analyze_btn = st.button("產生分析圖表", type="primary", use_container_width=True)

if analyze_btn:
    with st.spinner(f"正在分析 {stock_input} ..."):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_prices WHERE stock_id = ?", (stock_input,))
        count = cursor.fetchone()[0]
        conn.close()
        
        # 如果資料庫內沒資料或資料太少，觸發即時下載
        if count < 100:
            info_msg = st.empty()
            info_msg.info(f"資料庫尚未建立 {stock_input} 的完整資料，正在即時從雲端獲取中，請稍候約 5~10 秒...")
            success = fetch_data_for_stock(stock_input)
            info_msg.empty()  # 下載完成後清除訊息
            if not success:
                st.error(f"找不到代號 {stock_input} 的資料，請確認是否為有效代碼。")
                st.stop()
                
        fig = plot_divergence(stock_input)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            st.success("圖表載入完成！您可以拖曳放大縮小，或將滑鼠游標停留在圖表上查看詳細數據。")
        else:
            st.warning("該股票的歷史資料不足，無法計算背離（通常是因為上市時間太短）。")
