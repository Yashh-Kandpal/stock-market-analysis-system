# Indian Stock Market Analysis Dashboard

A full-stack web application for real-time Indian stock market data, built with **FastAPI**, **PostgreSQL**, and **React**.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite, Recharts, React Router |
| Backend | FastAPI (Python 3.12), async/await |
| Database | PostgreSQL 16 with SQLAlchemy (async) |
| Data Source | Alpha Vantage API (BSE-listed Indian stocks) |
| Container | Docker + Docker Compose |

---

## Project Structure

```
stock-app/
├── backend/
│   ├── main.py              # FastAPI app + CORS + lifespan
│   ├── database.py          # SQLAlchemy models + async engine
│   ├── alpha_vantage.py     # Alpha Vantage API client + parsers
│   ├── routers/
│   │   ├── stocks.py        # /api/stocks/* endpoints
│   │   └── watchlist.py     # /api/watchlist/* endpoints
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js    # Axios API client
│   │   ├── components/
│   │   │   ├── QuoteCard    # Live price card with auto-fetch
│   │   │   ├── StockChart   # OHLCV chart (Recharts, multi-interval)
│   │   │   ├── OHLCTable    # Tabular price history
│   │   │   ├── Card         # Base card container
│   │   │   └── Loader       # Spinner
│   │   ├── pages/
│   │   │   ├── Dashboard    # Popular Indian stocks grid
│   │   │   ├── StockDetail  # Chart + quote + watchlist toggle
│   │   │   ├── SearchPage   # Symbol search + add to watchlist
│   │   │   └── Watchlist    # Saved stocks
│   │   ├── App.jsx          # Router + sidebar layout
│   │   └── index.css        # CSS variables + global reset
│   ├── vite.config.js
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

---

## Quick Start (Docker — Recommended)

### 1. Get an Alpha Vantage API Key

Sign up free at [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)

The free tier allows **25 requests/day** and **5 requests/minute**.

### 2. Clone & Configure

```bash
git clone <your-repo>
cd stock-app
cp backend/.env.example backend/.env
# Edit backend/.env and set your ALPHA_VANTAGE_KEY
```

### 3. Start Everything

```bash
ALPHA_VANTAGE_KEY=your_key_here docker compose up --build
```

Or set it in a `.env` file at the project root:

```bash
# .env (project root — read by docker compose)
ALPHA_VANTAGE_KEY=your_key_here
```

Then just:

```bash
docker compose up --build
```

### 4. Open the App

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## Manual Setup (Without Docker)

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 running locally

### Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env from example
cp .env.example .env
# Edit .env: set DATABASE_URL and ALPHA_VANTAGE_KEY

# Create the database (run once)
psql -U postgres -c "CREATE USER stockuser WITH PASSWORD 'stockpass';"
psql -U postgres -c "CREATE DATABASE stockdb OWNER stockuser;"

# Start the server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Create .env
echo "VITE_API_URL=http://localhost:8000" > .env

npm run dev
```

---

## API Endpoints

### Stocks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stocks/popular` | List of popular Indian BSE stocks |
| GET | `/api/stocks/search?q=RELIANCE` | Search symbols via Alpha Vantage |
| GET | `/api/stocks/quote/{symbol}` | Latest global quote |
| GET | `/api/stocks/intraday/{symbol}?interval=5min` | Intraday OHLCV (cached in DB) |
| GET | `/api/stocks/daily/{symbol}?days=30` | Daily OHLCV (cached in DB) |
| GET | `/api/stocks/history/{symbol}?interval=1day` | Stored history from DB |

**Interval options for intraday:** `1min`, `5min`, `15min`, `30min`, `60min`

**Caching behaviour:** The backend first checks PostgreSQL for recent data. If found, it serves from DB without hitting the Alpha Vantage API. Add `?refresh=true` to force a fresh fetch.

### Watchlist

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/watchlist/` | Get all watchlist items |
| POST | `/api/watchlist/` | Add a stock `{ symbol, company_name, exchange }` |
| DELETE | `/api/watchlist/{symbol}` | Remove a stock |
| PATCH | `/api/watchlist/{symbol}` | Update notes/company name |

---

## Indian Stock Symbols

Alpha Vantage uses the `.BSE` suffix for BSE-listed stocks. Examples:

| Symbol | Company |
|--------|---------|
| `RELIANCE.BSE` | Reliance Industries |
| `TCS.BSE` | Tata Consultancy Services |
| `INFY.BSE` | Infosys |
| `HDFCBANK.BSE` | HDFC Bank |
| `ICICIBANK.BSE` | ICICI Bank |
| `SBIN.BSE` | State Bank of India |
| `WIPRO.BSE` | Wipro |
| `ITC.BSE` | ITC Limited |

Use the **Search** page to discover more symbols.

---

## Database Schema

### `stock_prices`
| Column | Type | Description |
|--------|------|-------------|
| id | serial PK | Auto ID |
| symbol | varchar(20) | e.g. `RELIANCE.BSE` |
| open/high/low/close | float | OHLC prices |
| volume | float | Trading volume |
| timestamp | datetime | Candle timestamp |
| interval | varchar(10) | `5min`, `1day`, etc. |
| fetched_at | datetime | When it was stored |

### `watchlist`
| Column | Type | Description |
|--------|------|-------------|
| id | serial PK | Auto ID |
| symbol | varchar(20) unique | Stock symbol |
| company_name | varchar(100) | Display name |
| exchange | varchar(10) | `BSE` or `NSE` |
| notes | text | Optional user notes |
| added_at | datetime | When added |

---

## Rate Limits & Caching

Alpha Vantage free tier: **5 requests/minute**, **25 requests/day**.

The app mitigates this with DB caching:
- Intraday data cached for 1 hour
- Daily data cached for the day
- Use `?refresh=true` to bypass cache and force a fresh API call

For heavier usage, consider upgrading to a paid Alpha Vantage plan or using a different data provider.

---

## Roadmap (Future Phases)

- [ ] Statistical analysis (Moving Averages, Z-score, Volatility)
- [ ] Anomaly detection with threshold flagging
- [ ] ML trend estimation (Linear Regression / ARIMA)
- [ ] Explanation layer — human-readable insight summaries
- [ ] Auto-refresh with polling or WebSocket streaming
- [ ] User authentication
- [ ] Portfolio tracking with P&L
- [ ] Candlestick chart view

---

## Environment Variables

### Backend (`backend/.env`)
```
DATABASE_URL=postgresql+asyncpg://stockuser:stockpass@localhost:5432/stockdb
ALPHA_VANTAGE_KEY=your_api_key_here
```

### Frontend (`frontend/.env`)
```
VITE_API_URL=http://localhost:8000
```
