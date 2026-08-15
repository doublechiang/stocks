# 台股 EPS 與股價背離分析系統 (Taiwan Stock Divergence Analyzer)

這是一個基於 Python 與 Streamlit 打造的量化分析儀表板。
系統能自動擷取台股公司的歷史財報 (EPS) 與還原股價，並透過互動式圖表，自動標示出潛在的「價值低估背離買點」與「泡沫高估背離風險」。

## 系統特色
- **即時資料獲取 (On-the-fly fetch)**：輸入股票代號後，若本地資料庫無資料，會自動從雲端 (FinMind, Yahoo Finance) 抓取並存入 SQLite。
- **還原股價分析**：使用 Yahoo Finance 的還原股價 (Adj Close)，完美解決除權息與股票分割導致的線圖斷層問題，呈現真實投資報酬。
- **TTM EPS 趨勢**：自動計算近四季 EPS 總和 (Trailing Twelve Months)，消除產業季節性因素。
- **視覺化互動圖表**：使用 Plotly 提供雙 Y 軸互動式圖表，並自動標示出背離訊號。

## 安裝與執行步驟

### 1. 安裝相依套件
請確認您的環境已安裝 Python 3.8 以上版本，並在專案根目錄下打開終端機執行：
```bash
pip install -r requirements.txt
```

### 2. 啟動 Streamlit 網頁應用程式
在終端機輸入以下指令啟動伺服器：
```bash
streamlit run app.py
```

### 3. 開始使用
指令執行後，終端機會顯示一個 Local URL（通常是 `http://localhost:8501`）。
請使用瀏覽器開啟該網址，在左上角的搜尋框輸入 4 碼的台股代號（例如：`2330`, `2317`, `2603`），點擊「產生分析圖表」即可即時運算並觀看結果。

## 資料庫與架構說明
- 本專案使用輕量級 SQLite 資料庫 (`stock_data.db`) 來快取歷史資料，減少重複抓取的 API 請求。
- 關於資料庫的 Schema 設計、實體關聯圖 (ERD) 與資料字典說明，請參考文件：[`docs/schema.md`](docs/schema.md)。
