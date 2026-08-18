import sqlite3
import os

# 設定資料庫檔案名稱
DB_PATH = 'stock_data.db'

def create_tables():
    print(f"開始初始化資料庫: {DB_PATH}")
    # 連結 SQLite 資料庫 (如果檔案不存在會自動建立)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 建立股票基本資料表 (stock_info)
    print("正在建立資料表: stock_info...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_info (
            stock_id TEXT PRIMARY KEY,
            stock_name TEXT NOT NULL,
            industry TEXT,
            update_date DATE
        )
    ''')

    # 2. 建立每股盈餘資料表 (eps_data)
    # 設定 UNIQUE (stock_id, year, quarter) 避免重複寫入同一季度的資料
    print("正在建立資料表: eps_data...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eps_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            eps_value REAL NOT NULL,
            announcement_date DATE,
            FOREIGN KEY (stock_id) REFERENCES stock_info (stock_id),
            UNIQUE (stock_id, year, quarter)
        )
    ''')

    # 3. 建立歷史股價表 (daily_prices)
    # 設定 UNIQUE (stock_id, date) 避免重複寫入同一天的資料
    print("正在建立資料表: daily_prices...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT NOT NULL,
            date DATE NOT NULL,
            close_price REAL NOT NULL,
            volume INTEGER,
            adj_close_price REAL,
            FOREIGN KEY (stock_id) REFERENCES stock_info (stock_id),
            UNIQUE (stock_id, date)
        )
    ''')

    # 儲存變更並關閉連線
    conn.commit()
    conn.close()
    print("資料庫與資料表建立完成！")

if __name__ == '__main__':
    create_tables()
