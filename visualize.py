import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB_PATH = 'stock_data.db'

def visualize_stock(stock_id):
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 取得股價資料
    df_price = pd.read_sql_query('''
        SELECT date, close_price 
        FROM daily_prices 
        WHERE stock_id = ? 
        ORDER BY date ASC
    ''', conn, params=(stock_id,))
    
    # 2. 取得 EPS 資料並計算 TTM
    df_eps = pd.read_sql_query('''
        SELECT year, quarter, eps_value, announcement_date 
        FROM eps_data 
        WHERE stock_id = ? 
        ORDER BY year ASC, quarter ASC
    ''', conn, params=(stock_id,))
    
    conn.close()
    
    if len(df_eps) < 4:
        print(f"{stock_id} 資料不足以視覺化")
        return
        
    # 計算 TTM EPS
    df_eps['ttm_eps'] = df_eps['eps_value'].rolling(window=4).sum()
    df_eps = df_eps.dropna(subset=['ttm_eps', 'announcement_date']).copy()
    df_eps.reset_index(drop=True, inplace=True)
    
    # 建立具有雙Y軸的圖表
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # --- 加入主圖表 ---
    # 加入股價線圖 (主Y軸)
    fig.add_trace(
        go.Scatter(x=df_price['date'], y=df_price['close_price'], 
                   name="收盤價", line=dict(color='#1f77b4', width=2)),
        secondary_y=False,
    )
    
    # 加入 TTM EPS 階梯圖 (副Y軸)
    # shape='hv' 代表用階梯狀 (Horizontal-Vertical) 繪製，很適合呈現一季一季跳動的財報數字
    fig.add_trace(
        go.Scatter(x=df_eps['announcement_date'], y=df_eps['ttm_eps'], 
                   name="近四季EPS (TTM)", line=dict(color='#ff7f0e', width=3, shape='hv')),
        secondary_y=True,
    )
    
    # --- 找出背離點並標記 ---
    # 這裡重新實作簡單的背離判斷來畫出標籤
    buy_signals_x, buy_signals_y = [], []
    risk_signals_x, risk_signals_y = [], []
    
    df_eps['prev_ttm_eps'] = df_eps['ttm_eps'].shift(1)
    
    for i in range(1, len(df_eps)):
        current_date = df_eps.loc[i, 'announcement_date']
        prev_date = df_eps.loc[i-1, 'announcement_date']
        
        # 抓取這兩個日期的對應股價
        current_price_df = df_price[df_price['date'] >= current_date]
        prev_price_df = df_price[df_price['date'] >= prev_date]
        
        if current_price_df.empty or prev_price_df.empty:
            continue
            
        current_price = current_price_df.iloc[0]['close_price']
        prev_price = prev_price_df.iloc[0]['close_price']
        
        eps_trend_up = df_eps.loc[i, 'ttm_eps'] > df_eps.loc[i, 'prev_ttm_eps']
        eps_trend_down = df_eps.loc[i, 'ttm_eps'] < df_eps.loc[i, 'prev_ttm_eps']
        
        price_trend_down = current_price < prev_price
        price_trend_up = current_price > prev_price
        
        # 低估背離 (標記在股價圖上)
        if eps_trend_up and price_trend_down:
            buy_signals_x.append(current_date)
            buy_signals_y.append(current_price)
            
        # 高估背離
        elif eps_trend_down and price_trend_up:
            risk_signals_x.append(current_date)
            risk_signals_y.append(current_price)
            
    # 加入標記點
    fig.add_trace(
        go.Scatter(x=buy_signals_x, y=buy_signals_y, mode='markers',
                   name="🌟 低估背離買點", 
                   marker=dict(color='green', size=12, symbol='triangle-up')),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=risk_signals_x, y=risk_signals_y, mode='markers',
                   name="⚠️ 高估背離風險", 
                   marker=dict(color='red', size=12, symbol='triangle-down')),
        secondary_y=False,
    )
    
    # --- 設定圖表外觀 ---
    fig.update_layout(
        title_text=f"<b>{stock_id} 股價與 EPS 背離分析圖</b>",
        xaxis_title="日期",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_yaxes(title_text="<b>股價 (元)</b>", secondary_y=False, color='#1f77b4')
    fig.update_yaxes(title_text="<b>TTM EPS (元)</b>", secondary_y=True, color='#ff7f0e')
    
    # 儲存成獨立的 HTML 檔案
    html_file = f"{stock_id}_divergence.html"
    fig.write_html(html_file)
    print(f"✅ 已經產生圖表：{html_file}")

if __name__ == '__main__':
    for stock in ['2330', '2317', '2454', '6412']:
        visualize_stock(stock)
