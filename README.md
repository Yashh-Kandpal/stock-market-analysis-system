# StockIN — Indian Stock Market Analysis System

A full-stack web application for real-time Indian stock market data with statistical analysis, machine learning predictions, and live model performance tracking. Built with **FastAPI**, **PostgreSQL**, and **React**.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite, Recharts, React Router, @react-oauth/google |
| Backend | FastAPI (Python 3.12), async/await, APScheduler |
| Database | PostgreSQL 16 with SQLAlchemy (async) |
| Data Source | Yahoo Finance via `yfinance` (NSE-listed stocks) |
| Auth | Google OAuth 2.0 + JWT |
| ML | statsmodels, scikit-learn, XGBoost, Prophet, Isolation Forest |
| Container | Docker + Docker Compose |

---

## Features

### Market Data
- Live BSE/NSE price quotes for 15 popular Indian stocks
- Intraday OHLCV charts (5m, 15m, 30m, 1h intervals)
- Daily charts with 1D, 3M, 1Y, 2Y timeframes
- Tabular data view with per-candle change %
- Smart DB caching — yfinance only called when data is stale

### Search
- Live search as you type (debounced, 400ms)
- Filters results to Indian exchanges (NSE/BSE)
- Per-user search history with clear/delete
- Add directly to watchlist from search results

### Watchlist
- Per-user watchlist (requires login)
- Add/remove stocks with optional notes
- Live quote cards with refresh button

### Statistical Analysis (6 modules, accordion UI)
| Module | What it computes |
|--------|-----------------|
| Moving Averages | SMA + EMA (configurable windows), golden/death cross signals |
| Volatility & Bollinger Bands | Annualised volatility, ATR, %B, bandwidth |
| RSI & MACD | RSI with OB/OS signals, MACD line + histogram + crossovers |
| Z-Score Anomaly Detection | Rolling Z-score on price + volume, combined anomaly flagging |
| Support & Resistance | Pivot points R1–R3, S1–S3 from last candle |
| Returns & Risk | Sharpe ratio (rf=6%), max drawdown, skewness, kurtosis, win rate |

All modules support configurable timeframes (3M, 6M, 1Y, 2Y). Panels are collapsed by default and load data only when opened.

### ML Predictions (5 models, accordion UI)
| Model | Predicts | Training time |
|-------|----------|---------------|
| ARIMA | Next 7–30 day price forecast with 95% confidence bands | ~5 sec |
| Prophet | 14–90 day forecast with trend + seasonality decomposition | ~15 sec |
| Linear/Logistic Regression | Next-day return magnitude + direction | ~1 sec |
| XGBoost | Next-day + 5-day direction with confidence score | ~5 sec |
| Isolation Forest | Multi-dimensional anomaly detection (not directional) | ~2 sec |

Results are cached in PostgreSQL for 24 hours — subsequent loads are instant.

### Model Performance Tracking
- Predictions logged automatically every time the ML page is visited
- **Automated batch predictions** run daily at 4:00 PM IST via APScheduler for all tracked stocks
- Actuals fetched automatically from yfinance after market close — resilient to server downtime (backfill on next startup)
- Model comparison table with directional accuracy, MAE, best/worst stock per model
- Confidence calibration analysis — checks if model confidence scores are meaningful
- Raw prediction log with per-row correct/incorrect status
- Fully dynamic — new models appear automatically without code changes

### User Authentication
- Google OAuth 2.0 login
- JWT tokens (30-day expiry, persistent across server restarts)
- Per-user watchlist and search history
- Avatar + name shown in sidebar

### UI
- **Light / Dark mode** toggle (persisted to localStorage)
- **Collapsible sidebar** — expands to 220px (labels) or collapses to 60px (icons only), persisted
- Dark theme: deep navy/slate palette
- Light theme: clean white/grey palette
- Fully responsive

---

## Project Structure

```
stock-app/
├── backend/
│   ├── main.py                  # FastAPI app, lifespan, scheduler start
│   ├── database.py              # All SQLAlchemy models + async engine
│   ├── auth.py                  # JWT creation/verification, Google token verification
│   ├── yahoo_finance.py         # yfinance API client + parsers
│   ├── backfill.py              # Fills in actual prices for pending predictions
│   ├── batch_predictor.py       # Runs all models for all stocks automatically
│   ├── prediction_logger.py     # Logs predictions to DB after each model run
│   ├── scheduler.py             # APScheduler — 4 PM IST daily batch + backfill
│   ├── ml/
│   │   ├── features.py          # Feature engineering (50+ technical indicators)
│   │   ├── arima_model.py       # ARIMA with auto (p,d,q) selection
│   │   ├── linear_model.py      # Ridge regression + Logistic regression
│   │   ├── xgboost_model.py     # XGBoost classifier + regressor
│   │   ├── isolation_forest.py  # Isolation Forest anomaly detection
│   │   ├── prophet_model.py     # Prophet with Indian market seasonality
│   │   └── predictor.py        # Unified interface with DB caching
│   ├── analysis/
│   │   └── statistics.py        # All statistical computations
│   ├── routers/
│   │   ├── stocks.py            # /api/stocks/*
│   │   ├── watchlist.py         # /api/watchlist/* (auth required)
│   │   ├── analysis.py          # /api/analysis/*
│   │   ├── ml.py                # /api/ml/*
│   │   ├── performance.py       # /api/performance/*
│   │   ├── auth.py              # /api/auth/*
│   │   └── search_history.py    # /api/search-history/*
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js        # Axios client + all API modules
│   │   ├── context/
│   │   │   ├── AuthContext.jsx  # Auth state + JWT management
│   │   │   ├── ThemeContext.jsx # Light/dark mode
│   │   │   └── SidebarContext.jsx # Sidebar expand/collapse
│   │   ├── components/
│   │   │   ├── QuoteCard        # Live price card
│   │   │   ├── StockChart       # Multi-interval OHLCV chart
│   │   │   ├── OHLCTable        # Tabular price data
│   │   │   ├── StatCard         # Single metric display
│   │   │   ├── PredictionBadge  # UP/DOWN direction badge
│   │   │   ├── TimeframeSelector # Days picker
│   │   │   ├── ProtectedRoute   # Auth guard
│   │   │   ├── Card             # Base container
│   │   │   └── Loader           # Spinner
│   │   ├── pages/
│   │   │   ├── Dashboard        # Popular stocks grid with live quotes
│   │   │   ├── StockDetail      # Quote + chart + data table + nav to analysis/ML
│   │   │   ├── SearchPage       # Live search + history
│   │   │   ├── Watchlist        # Per-user saved stocks
│   │   │   ├── AnalysisPage     # 6 statistical analysis accordion panels
│   │   │   ├── MLPage           # 5 ML model accordion panels
│   │   │   ├── PerformancePage  # Model accuracy dashboard
│   │   │   └── LoginPage        # Google OAuth login
│   │   ├── App.jsx
│   │   └── index.css            # CSS variables (light + dark themes)
│   ├── vite.config.js
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Google OAuth Client ID (for login)

### 1. Clone & configure

```bash
git clone https://github.com/Yashh-Kandpal/stock-market-analysis-system
cd stock-market-analysis-system
```

Create `backend/.env`:
```
DATABASE_URL=postgresql+asyncpg://stockuser:stockpass@localhost:5432/stockdb
JWT_SECRET=generate-with-python-secrets-token-hex-32
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

To generate a JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Database setup (run once)

```bash
psql -U postgres -c "CREATE USER stockuser WITH PASSWORD 'stockpass';"
psql -U postgres -c "CREATE DATABASE stockdb OWNER stockuser;"
```

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Open the app

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

---

## Google OAuth Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. Add `http://localhost:5173` to Authorised JavaScript origins
5. Copy the Client ID into both `.env` files

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/google` | Exchange Google token for JWT |
| GET | `/api/auth/me` | Get current user info |

### Stocks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stocks/popular` | 15 popular NSE stocks |
| GET | `/api/stocks/search?q=RELIANCE` | Search by name or ticker |
| GET | `/api/stocks/quote/{symbol}` | Latest quote |
| GET | `/api/stocks/intraday/{symbol}?interval=5min` | Intraday OHLCV |
| GET | `/api/stocks/daily/{symbol}?days=30` | Daily OHLCV |

### Statistical Analysis
All endpoints accept a `days` parameter (90–730).

| Endpoint | Description |
|----------|-------------|
| `/api/analysis/{symbol}/moving-averages` | SMA + EMA, configurable windows |
| `/api/analysis/{symbol}/volatility` | Rolling vol, ATR, Bollinger Bands |
| `/api/analysis/{symbol}/rsi` | RSI with OB/OS levels |
| `/api/analysis/{symbol}/macd` | MACD + signal + histogram |
| `/api/analysis/{symbol}/anomalies` | Z-score anomaly detection |
| `/api/analysis/{symbol}/support-resistance` | Pivot points |
| `/api/analysis/{symbol}/returns` | Sharpe, drawdown, skewness |

### ML Predictions
All endpoints accept a `days` parameter for training window.

| Endpoint | Description |
|----------|-------------|
| `/api/ml/{symbol}/arima` | ARIMA price forecast |
| `/api/ml/{symbol}/prophet` | Prophet multi-week forecast |
| `/api/ml/{symbol}/linear` | Linear + Logistic Regression |
| `/api/ml/{symbol}/xgboost` | XGBoost direction prediction |
| `/api/ml/{symbol}/isolation-forest` | Isolation Forest anomalies |

### Model Performance
| Endpoint | Description |
|----------|-------------|
| `/api/performance/summary` | Accuracy per model across all stocks |
| `/api/performance/log` | Raw prediction log |
| `/api/performance/symbol/{symbol}` | Per-stock breakdown |
| `/api/performance/calibration` | Confidence calibration analysis |

### Watchlist & Search History (auth required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/watchlist/` | Get or add watchlist items |
| DELETE | `/api/watchlist/{symbol}` | Remove a stock |
| GET/POST | `/api/search-history/` | Get or save search history |
| DELETE | `/api/search-history/` | Clear all history |

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `users` | Google OAuth users (id, email, name, avatar) |
| `stock_prices` | OHLCV cache (symbol, timestamp, interval, OHLCV) |
| `watchlist` | Per-user saved stocks |
| `search_history` | Per-user search queries |
| `ml_results` | Cached ML model outputs (24hr TTL) |
| `prediction_log` | Daily predictions vs actuals for accuracy tracking |

---

## ML Feature Engineering

The ML module computes 50+ features from raw OHLCV data:

- **Price features** — returns, log returns, HL ratio, open-close ratio, gap
- **Trend** — SMA/EMA (9, 20, 50) ratios, MA crossover signals, slope
- **Momentum** — RSI (14), MACD, Rate of Change (5/10/20d), Stochastic %K/%D
- **Volatility** — rolling annualised vol, ATR ratio, Bollinger %B, bandwidth
- **Volume** — relative volume, volume Z-score, OBV ratio, PVT
- **Lag features** — 1-day and 2-day lags of key indicators

---

## Automated Batch Predictions

The scheduler runs automatically inside the FastAPI process:

- **4:00 PM IST daily (Mon–Fri)** — runs ARIMA, Prophet, Linear, XGBoost for all 15 popular stocks + any stock in any user's watchlist
- **4:15 PM IST daily** — fetches actual closing prices and fills in prediction results
- **On every server startup** — backfills any missing actuals from yfinance history

This means predictions are logged and evaluated even if you don't open the app. Missing a day is safe — backfill catches up on next startup.

---

## Indian Stock Symbols

Yahoo Finance uses `.NS` suffix for NSE stocks:

| Symbol | Company |
|--------|---------|
| `RELIANCE.NS` | Reliance Industries |
| `TCS.NS` | Tata Consultancy Services |
| `INFY.NS` | Infosys |
| `HDFCBANK.NS` | HDFC Bank |
| `ICICIBANK.NS` | ICICI Bank |
| `SBIN.NS` | State Bank of India |
| `WIPRO.NS` | Wipro |
| `ITC.NS` | ITC Limited |
| `BAJFINANCE.NS` | Bajaj Finance |
| `MARUTI.NS` | Maruti Suzuki |
| `AXISBANK.NS` | Axis Bank |
| `KOTAKBANK.NS` | Kotak Mahindra Bank |
| `LT.NS` | Larsen & Toubro |
| `TECHM.NS` | Tech Mahindra |
| `HINDUNILVR.NS` | Hindustan Unilever |

---

## Environment Variables

### `backend/.env`
```
DATABASE_URL=postgresql+asyncpg://stockuser:stockpass@localhost:5432/stockdb
JWT_SECRET=your-32-char-random-string
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### `frontend/.env`
```
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

---

## Dependencies

### Backend (key packages)
```
fastapi, uvicorn, sqlalchemy[asyncio], asyncpg
yfinance, pandas, numpy
statsmodels          # ARIMA
scikit-learn         # Linear regression, Isolation Forest
xgboost              # XGBoost
prophet              # Prophet forecasting
apscheduler          # Scheduled batch predictions
python-jose          # JWT
google-auth          # Google OAuth verification
```

### Frontend (key packages)
```
react, react-router-dom
recharts             # All charts
axios                # HTTP client
@react-oauth/google  # Google login button
lucide-react         # Icons
```

---

## Disclaimer

This application is built for academic and educational purposes as part of a university project. It does not constitute financial advice. ML predictions are probabilistic estimates based on historical patterns — past accuracy does not guarantee future performance.
