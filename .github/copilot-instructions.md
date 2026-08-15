# Copilot Instructions - Taiwan Stock Divergence Analyzer

## Quick Reference

### Running the Application
- **Start Streamlit app**: `streamlit run app.py`
- **Run tests**: `python test.py`
- **Initialize database**: `python init_db.py`
- **Fetch stock data**: `python fetch_history_data.py`
- **Single stock analysis**: Add stock_id parameter; app auto-fetches from FinMind/Yahoo Finance if not cached

### Installation & Environment
- Python 3.8+ required
- Install dependencies: `pip install -r requirements.txt`
- Dependencies: pandas, FinMind, yfinance, plotly, streamlit
- SQLite database auto-creates at `stock_data.db`

## Architecture Overview

### Core Workflow
The system has three main execution flows:

1. **Data Ingestion**: FinMind API + Yahoo Finance
   - `fetch_stock_info.py`: Pulls Taiwan stock list (filters 4-digit codes)
   - `fetch_history_data.py`: Fetches financial statements and price history
   - `init_db.py`: Creates SQLite schema with three tables

2. **Analysis**: TTM EPS & Price Divergence Detection
   - `analyze_divergence.py`: Calculates trailing twelve-month (TTM) EPS, detects undervaluation (buy signal) and overvaluation (risk signal) by comparing against historical PE multiples
   - Uses `announcement_date` (not fiscal quarter end) to align EPS with actual price data—critical to avoid look-ahead bias

3. **Visualization**: Interactive Streamlit Dashboard
   - `app.py`: Streamlit interface with dynamic fetch on missing data
   - `visualize.py`: Plotly dual-axis charts (price + TTM EPS)
   - Automatically detects divergence events and annotates chart

### Database Schema (SQLite)
Three-table design with foreign keys to `stock_id`:

- **stock_info**: Master list of tracked stocks (stock_id, name, industry, update_date)
- **eps_data**: Quarterly earnings (id, stock_id, year, quarter, eps_value, **announcement_date**)
- **daily_prices**: Daily OHLCV (id, stock_id, date, close_price, volume, adj_close_price)

Key constraint: `(stock_id, year, quarter)` UNIQUE on eps_data; `(stock_id, date)` UNIQUE on daily_prices
Refer to `docs/schema.md` for ERD and full data dictionary.

## Key Conventions

### Data Alignment & Timing
- **announcement_date** in eps_data is the actual fiscal report release date, not quarter-end. This is mandatory for price alignment—never use the fiscal quarter end date.
- `estimate_announcement_date()` in app.py provides fallback logic (Q1→May 15, Q2→Aug 14, Q3→Nov 14, Q4→Mar 31 next year).
- Always fetch **adjusted close price** (adj_close_price) from Yahoo Finance, never raw close—this accounts for splits and dividends.

### TTM EPS Calculation
- TTM (Trailing Twelve Months) = sum of the most recent 4 quarters' EPS
- Eliminates seasonal noise in earnings
- Used as denominator for P/E multiple analysis
- Plotted on secondary Y-axis against price on primary Y-axis

### External Data Sources
- **FinMind**: `api.taiwan_stock_financial_statement()` → EPS, returns data by quarter in form `{type: 'EPS', value: X, date: YYYY-MM-DD}`
- **Yahoo Finance**: `yf.Ticker(f"{stock_id}.TW").history()` → Daily prices, use `.Adj Close` not `.Close`
- Both may have gaps; handle missing dates gracefully

### File Naming & Organization
- Main app: `app.py` (Streamlit entry point)
- Data ops: `fetch_*.py`, `init_db.py`, `alter_db.py`
- Analysis: `analyze_divergence.py`
- Visualization: `visualize.py`
- Utilities: `test.py` (quick test harness)
- Configuration: Constants like `DB_PATH`, `START_DATE` at top of each module

### Divergence Signal Detection
Detect when price diverges from EPS fundamentals:
- **Undervaluation (buy)**: Stock price at historical low P/E despite high TTM EPS
- **Overvaluation (risk)**: Stock price at historical high P/E despite low TTM EPS
- Logic lives in `analyze_divergence.py`; visual annotation in `visualize.py`

## Testing & Validation
- `test.py`: Ad-hoc test for FinMind API integration (fetches sample Q/E data for stock 2330)
- No unit test framework yet—focus on end-to-end validation via Streamlit
- Validate divergence logic: manually verify TTM calculation against raw EPS values and compare chart annotations against hand-calculated P/E

## Common Workflows

### Adding a New Stock
1. Input stock_id in Streamlit sidebar → app auto-triggers `fetch_data_for_stock()`
2. If stock not in DB: FinMind pull → parse EPS by quarter → Yahoo fetch → insert daily_prices
3. On success: stock_info, eps_data, daily_prices rows created; chart appears immediately

### Fixing Data Issues
- `alter_db.py`: Manual SQL updates (rebuild affected rows or truncate/refetch)
- Common issue: incorrect announcement_date → TTM alignment off → divergence signals wrong
- Verify via SQL: `SELECT * FROM eps_data WHERE stock_id = '2330' ORDER BY announcement_date`

### Adding New Divergence Logic
- Core formula in `analyze_divergence.py` under `analyze_divergence()`
- Add new metrics (e.g., P/B, dividend yield) by extending eps_data or daily_prices schema
- Update chart in `visualize.py` if adding new trace/subplot
