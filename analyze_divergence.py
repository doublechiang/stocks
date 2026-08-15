import sqlite3
import pandas as pd

DB_PATH = 'stock_data.db'

def get_closest_trading_price(cursor, stock_id, target_date):
    """
    獲取指定日期當天或之後最近一個交易日的收盤價
    (因為財報公佈日可能是假日，所以往後找最近的開盤日)
    """
    cursor.execute('''
        SELECT date, adj_close_price as close_price 
        FROM daily_prices 
        WHERE stock_id = ? AND date >= ? 
        ORDER BY date ASC 
        LIMIT 1
    ''', (stock_id, target_date))
    result = cursor.fetchone()
    if result:
        return result[0], result[1]
    return None, None

def analyze_divergence():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 取出所有已經有 EPS 資料的股票
    cursor.execute("SELECT DISTINCT stock_id FROM eps_data")
    stocks = [row[0] for row in cursor.fetchall()]
    
    for stock_id in stocks:
        print(f"\n================ 股票代號：{stock_id} ================")
        
        # 1. 撈出該股票所有 EPS 並按時間排序
        df_eps = pd.read_sql_query('''
            SELECT year, quarter, eps_value, announcement_date 
            FROM eps_data 
            WHERE stock_id = ? 
            ORDER BY year ASC, quarter ASC
        ''', conn, params=(stock_id,))
        
        if len(df_eps) < 5:
            print("資料筆數不足以計算近四季(TTM)與歷史比較，略過。")
            continue
            
        # 2. 計算 TTM EPS (滾動加總近四季)
        df_eps['ttm_eps'] = df_eps['eps_value'].rolling(window=4).sum()
        
        # 3. 獲取每次財報公佈時的實際股價
        price_dates = []
        prices = []
        for index, row in df_eps.iterrows():
            if pd.isna(row['announcement_date']):
                price_dates.append(None)
                prices.append(None)
                continue
                
            p_date, p_price = get_closest_trading_price(cursor, stock_id, row['announcement_date'])
            price_dates.append(p_date)
            prices.append(p_price)
            
        df_eps['price_date'] = price_dates
        df_eps['close_price'] = prices
        
        # 移除無效資料 (例如最前面幾季算不出TTM，或找不到股價)
        df_valid = df_eps.dropna(subset=['ttm_eps', 'close_price']).copy()
        df_valid.reset_index(drop=True, inplace=True)
        
        if len(df_valid) < 2:
            continue
            
        # 4. 計算與「上一次財報公佈時」的差異，用來判斷趨勢方向
        df_valid['prev_ttm_eps'] = df_valid['ttm_eps'].shift(1)
        df_valid['prev_close_price'] = df_valid['close_price'].shift(1)
        
        divergence_found = False
        
        # 從第二筆開始比對
        for index, row in df_valid.iterrows():
            if index == 0: continue
            
            # 判斷 EPS 與股價的趨勢
            eps_trend_up = row['ttm_eps'] > row['prev_ttm_eps']
            eps_trend_down = row['ttm_eps'] < row['prev_ttm_eps']
            
            price_trend_up = row['close_price'] > row['prev_close_price']
            price_trend_down = row['close_price'] < row['prev_close_price']
            
            # A. 價值低估背離：公司越賺越多，股價卻越跌越低
            if eps_trend_up and price_trend_down:
                divergence_found = True
                print(f"🌟 [低估背離買點] {row['year']} Q{row['quarter']} 財報公佈時 ({row['price_date']}):")
                print(f"   ➤ 基本面成長: 近四季EPS 從 {row['prev_ttm_eps']:.2f} 升至 {row['ttm_eps']:.2f}")
                print(f"   ➤ 股價卻下跌: 從 {row['prev_close_price']:.1f} 跌至 {row['close_price']:.1f}")
                print("-" * 55)
                
            # B. 泡沫高估背離：公司獲利衰退，股價卻被炒作上天
            elif eps_trend_down and price_trend_up:
                divergence_found = True
                print(f"⚠️ [高估背離風險] {row['year']} Q{row['quarter']} 財報公佈時 ({row['price_date']}):")
                print(f"   ➤ 基本面衰退: 近四季EPS 從 {row['prev_ttm_eps']:.2f} 降至 {row['ttm_eps']:.2f}")
                print(f"   ➤ 股價卻炒高: 從 {row['prev_close_price']:.1f} 漲至 {row['close_price']:.1f}")
                print("-" * 55)
                
        if not divergence_found:
            print("近幾年內沒有發現明顯的背離現象。")
            
    conn.close()
    print("\n分析完成！")

if __name__ == '__main__':
    analyze_divergence()
