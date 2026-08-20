import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader
from datetime import timedelta
import yfinance as yf
from flask import Flask, render_template, request
import init_db

# 確保資料庫與資料表已初始化
init_db.create_tables()

app = Flask(__name__)

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
                
        # 2. 抓取股價 (上市用 .TW, 上櫃用 .TWO)
        price_df = pd.DataFrame()
        for suffix in ['.TW', '.TWO']:
            yf_ticker = f"{stock_id}{suffix}"
            ticker = yf.Ticker(yf_ticker)
            price_df = ticker.history(start=START_DATE, auto_adjust=False)
            if not price_df.empty:
                break

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
        print(f"下載失敗: {e}")
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


@app.route('/')
def index():
    """首頁：顯示搜尋表單"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """分析路由：接收股票代號，回傳含圖表的頁面"""
    stock_id = request.form.get('stock_id', '').strip()
    
    if not stock_id:
        return render_template('index.html', error="請輸入股票代號。", error_type="warning")
    
    # 檢查資料庫是否有足夠資料，沒有就即時下載
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices WHERE stock_id = ?", (stock_id,))
    count = cursor.fetchone()[0]
    conn.close()
    
    if count < 100:
        success = fetch_data_for_stock(stock_id)
        if not success:
            return render_template('index.html',
                                   stock_id=stock_id,
                                   error=f"找不到代號 {stock_id} 的資料，請確認是否為有效代碼。",
                                   error_type="danger")
    
    fig = plot_divergence(stock_id)
    if fig:
        # 將 Plotly 圖表轉成 HTML 片段嵌入模板
        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return render_template('index.html', stock_id=stock_id, chart_html=chart_html)
    else:
        return render_template('index.html',
                               stock_id=stock_id,
                               error="該股票的歷史資料不足，無法計算背離（通常是因為上市時間太短）。",
                               error_type="warning")


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
