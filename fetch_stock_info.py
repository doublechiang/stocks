import sqlite3
import pandas as pd
from FinMind.data import DataLoader
from datetime import date

DB_PATH = 'stock_data.db'

def update_stock_info():
    print("正在初始化 FinMind API...")
    api = DataLoader()
    
    print("正在從 FinMind 獲取台股清單資料...")
    try:
        # 取得台股清單
        df = api.taiwan_stock_info()
    except Exception as e:
        print(f"獲取資料失敗: {e}")
        return

    # 我們通常只分析一般的上市 (twse) 與 上櫃 (tpex) 公司
    # 為了過濾掉權證、ETF等，我們簡單透過代碼長度 (一般公司為4碼) 來篩選
    df['stock_id_len'] = df['stock_id'].astype(str).str.len()
    mask = (df['type'].isin(['twse', 'tpex'])) & (df['stock_id_len'] == 4)
    stock_df = df[mask].copy()
    
    print(f"篩選後共找到 {len(stock_df)} 檔上市櫃公司股票。")
    
    print("正在將資料更新至 SQLite 資料庫...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    count = 0
    
    # 逐筆寫入資料庫
    for index, row in stock_df.iterrows():
        # 使用 INSERT OR REPLACE (若存在則覆蓋更新)
        cursor.execute('''
            INSERT OR REPLACE INTO stock_info (stock_id, stock_name, industry, update_date)
            VALUES (?, ?, ?, ?)
        ''', (row['stock_id'], row['stock_name'], row.get('industry_category', ''), today))
        count += 1
        
    conn.commit()
    conn.close()
    
    print(f"成功更新 {count} 筆股票基本資料！")

if __name__ == '__main__':
    update_stock_info()
