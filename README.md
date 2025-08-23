# 🌐 Market Data API

FastAPI-based real-time market data collection and API service with SQLite storage and comprehensive analytics.

## 🚀 Features

- **📡 Real-time Data**: Live stock prices and market data
- **🗄️ Data Storage**: SQLite database with efficient indexing
- **🔄 Auto Collection**: Background data collection every 15 minutes
- **📊 Analytics API**: Technical indicators and metrics
- **🌐 RESTful API**: FastAPI with automatic documentation

## 🛠️ Installation

```bash
git clone https://github.com/olaitanojo/market-data-api.git
cd market-data-api
pip install fastapi uvicorn pandas numpy yfinance sqlite3
python app.py
```

Visit http://localhost:8000/docs for API documentation.

## 📡 API Endpoints

- **GET /** - API overview and endpoints
- **GET /symbols** - Available stock symbols
- **GET /data/{symbol}** - Historical stock data
- **GET /realtime/{symbol}** - Real-time price data
- **GET /analytics/{symbol}** - Technical analysis metrics
- **POST /collect** - Manual data collection trigger

## 📊 Sample Response

```json
{
  "symbol": "AAPL",
  "price": 175.43,
  "change": +2.15,
  "change_percent": 1.24,
  "volume": 52847392,
  "market_cap": 2847392847392
}
```

## 🎯 Use Cases

- **Trading Bots**: Real-time data feeds
- **Analytics**: Historical data analysis
- **Monitoring**: Portfolio tracking
- **Research**: Market data collection

---
Created by [olaitanojo](https://github.com/olaitanojo)
