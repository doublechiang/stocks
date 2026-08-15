import sqlite3
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import time

DB_PATH = 'stock_data.db'
# 只抓取台灣前三大權值股做測試
STOCKS = ['2330', '2317', '2454','6412']
START_DATE = '2020-01-01'

def estimate_announcement_date(period_end_str):
    """
    推估財報公佈日 (避免未來函數)：
    台灣規定財報公佈期限大約如下：
    Q1 (03-31結束) -> 05-15前
    Q2 (06-30結束) -> 08-14前
    Q3 (09-30結束) -> 11-14前
    Q4 (12-31結束) -> 隔年 03-31前
    """
    dt = pd.to_datetime(period_end_str)
    if dt.month == 3:
        return f"{dt.year}-05-15"
    elif dt.month == 6:
        return f"{dt.year}-08-14"
    elif dt.month == 9:
        return f"{dt.year}-11-14"
    elif dt.month == 12:
        return f"{dt.year + 1}-03-31"
    else:
        # 例外狀況往後推45天
        return (dt + timedelta(days=45)).strftime('%Y-%m-%d')

def fetch_and_save_data():
    api = DataLoader()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for stock_id in STOCKS:
        print(f"\n--- 正在處理 {stock_id} ---")
        
        # 1. 抓取 EPS (來自綜合損益表)
        print(f"抓取 {stock_id} 歷史財報...")
        try:
            fs_df = api.taiwan_stock_financial_statement(stock_id=stock_id, start_date=START_DATE)
            eps_df = fs_df[fs_df['type'] == 'EPS'].copy()
            
            eps_count = 0
            for _, row in eps_df.iterrows():
                dt = pd.to_datetime(row['date'])
                year = dt.year
                quarter = (dt.month - 1) // 3 + 1
                announce_date = estimate_announcement_date(row['date'])
                
                cursor.execute('''
                    INSERT OR REPLACE INTO eps_data (stock_id, year, quarter, eps_value, announcement_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (stock_id, year, quarter, row['value'], announce_date))
                eps_count += 1
            print(f"成功存入 {eps_count} 筆 EPS 資料。")
            
        except Exception as e:
            print(f"抓取 {stock_id} EPS 失敗: {e}")
            
        time.sleep(1) # 暫停1秒，避免呼叫太快被鎖
        
        # 2. 抓取每日股價
        print(f"抓取 {stock_id} 歷史股價...")
        try:
            price_df = api.taiwan_stock_daily(stock_id=stock_id, start_date=START_DATE)
            price_count = 0
            for _, row in price_df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_prices (stock_id, date, close_price, volume)
                    VALUES (?, ?, ?, ?)
                ''', (stock_id, row['date'], row['close'], row['Trading_Volume']))
                price_count += 1
            print(f"成功存入 {price_count} 筆股價資料。")
            
        except Exception as e:
            print(f"抓取 {stock_id} 股價失敗: {e}")
            
        time.sleep(1)
        
    conn.commit()
    conn.close()
    print("\n所有測試資料抓取與寫入完成！")

if __name__ == '__main__':
    fetch_and_save_data()
