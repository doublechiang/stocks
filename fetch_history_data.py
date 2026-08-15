import sqlite3
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import yfinance as yf
import time

DB_PATH = 'stock_data.db'
STOCKS = ['2330', '2317', '2454']
START_DATE = '2020-01-01'

def estimate_announcement_date(period_end_str):
    dt = pd.to_datetime(period_end_str)
    if dt.month == 3: return f"{dt.year}-05-15"
    elif dt.month == 6: return f"{dt.year}-08-14"
    elif dt.month == 9: return f"{dt.year}-11-14"
    elif dt.month == 12: return f"{dt.year + 1}-03-31"
    else: return (dt + timedelta(days=45)).strftime('%Y-%m-%d')

def fetch_and_save_data():
    api = DataLoader()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for stock_id in STOCKS:
        print(f"\n--- 正在處理 {stock_id} ---")
        
        # 1. 抓取 EPS (FinMind)
        print(f"抓取 {stock_id} 歷史財報 (FinMind)...")
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
            
        time.sleep(1)
        
        # 2. 抓取每日股價含還原股價 (yfinance)
        print(f"抓取 {stock_id} 歷史股價 (yfinance)...")
        try:
            # 加上 .TW 代表台灣上市股票
            yf_ticker = f"{stock_id}.TW"
            ticker = yf.Ticker(yf_ticker)
            # auto_adjust=False 才會同時回傳 Close 與 Adj Close
            price_df = ticker.history(start=START_DATE, auto_adjust=False)
            
            price_count = 0
            for date_idx, row in price_df.iterrows():
                date_str = date_idx.strftime('%Y-%m-%d')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_prices (stock_id, date, close_price, volume, adj_close_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (stock_id, date_str, float(row['Close']), int(row['Volume']), float(row['Adj Close'])))
                price_count += 1
            print(f"成功存入 {price_count} 筆含還原股價的歷史資料。")
            
        except Exception as e:
            print(f"抓取 {stock_id} 股價失敗: {e}")
            
        time.sleep(1)
        
    conn.commit()
    conn.close()
    print("\n所有混血版資料抓取與寫入完成！")

if __name__ == '__main__':
    fetch_and_save_data()
