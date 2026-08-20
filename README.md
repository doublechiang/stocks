# 台股 EPS 與股價背離分析系統 (Taiwan Stock Divergence Analyzer)

這是一個基於 Python 與 Flask 打造的量化分析 Web 應用程式。
系統能自動擷取台股公司的歷史財報 (EPS) 與還原股價，並透過互動式圖表，自動標示出潛在的「價值低估背離買點」與「泡沫高估背離風險」。

**線上版**：https://stock-app-213290980608.asia-east1.run.app/

## 系統特色
- **即時資料獲取 (On-the-fly fetch)**：輸入股票代號後，若本地資料庫無資料，會自動從雲端 (FinMind, Yahoo Finance) 抓取並存入 SQLite。
- **還原股價分析**：使用 Yahoo Finance 的還原股價 (Adj Close)，完美解決除權息與股票分割導致的線圖斷層問題，呈現真實投資報酬。
- **TTM EPS 趨勢**：自動計算近四季 EPS 總和 (Trailing Twelve Months)，消除產業季節性因素。
- **視覺化互動圖表**：使用 Plotly 提供雙 Y 軸互動式圖表，並自動標示出背離訊號。

## 安裝與執行

### 1. 安裝相依套件
請確認您的環境已安裝 Python 3.8 以上版本，並在專案根目錄下打開終端機執行：
```bash
pip install -r requirements.txt
```

### 2. 本地啟動（開發模式）
```bash
python app.py
```
啟動後，用瀏覽器開啟 http://localhost:8080 即可使用。

> Flask 開發模式下會自動啟用 hot-reload，修改程式碼後會自動重啟伺服器。

### 3. 本地啟動（生產模式，使用 gunicorn）
```bash
gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 --timeout 120 app:app
```

### 4. 使用 Docker
```bash
docker build -t stock-app .
docker run -p 8080:8080 stock-app
```
啟動後同樣開啟 http://localhost:8080。

### 5. 開始使用
在搜尋框輸入 4 碼的台股代號（例如：`2330`, `2317`, `2603`），點擊「產生分析圖表」即可即時運算並觀看結果。

## 部署
本專案透過 GitHub Actions CI/CD 自動部署至 Google Cloud Run。
推送到 `main` 分支後即自動觸發部署流程。

## 資料庫與架構說明
- 本專案使用輕量級 SQLite 資料庫 (`stock_data.db`) 來快取歷史資料，減少重複抓取的 API 請求。
- 關於資料庫的 Schema 設計、實體關聯圖 (ERD) 與資料字典說明，請參考文件：[`docs/schema.md`](docs/schema.md)。
