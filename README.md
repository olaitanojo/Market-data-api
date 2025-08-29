# 🌐 Market Data API

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real--Time-green)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready **real-time market data API** built with FastAPI, featuring multi-source data collection, WebSocket streaming, SQLite storage, comprehensive analytics, and enterprise-grade CI/CD pipeline integration.

## 📋 Table of Contents
- [🏗️ Architecture](#%EF%B8%8F-architecture)
- [🚀 Features](#-features)
- [🛠️ Installation](#%EF%B8%8F-installation)
- [📊 API Endpoints](#-api-endpoints)
- [🔌 WebSocket Streaming](#-websocket-streaming)
- [📊 Sample Responses](#-sample-responses)
- [🎯 Use Cases](#-use-cases)
- [🚀 Deployment](#-deployment)
- [🔧 Configuration](#-configuration)
- [📝 License](#-license)

## 🏗️ Architecture

### System Overview
```mermaid
graph TB
    subgraph "Client Layer"
        A1[Web Clients]
        A2[Trading Bots]
        A3[Analytics Tools]
        A4[Mobile Apps]
    end
    
    subgraph "API Gateway Layer"
        B1[FastAPI Server]
        B2[Authentication]
        B3[Rate Limiting]
        B4[Request Validation]
    end
    
    subgraph "WebSocket Layer"
        C1[WebSocket Server]
        C2[Connection Manager]
        C3[Real-time Publisher]
        C4[Subscription Manager]
    end
    
    subgraph "Data Processing Layer"
        D1[Data Collector]
        D2[Data Validator]
        D3[Analytics Engine]
        D4[Technical Indicators]
        D5[Background Tasks]
    end
    
    subgraph "Storage Layer"
        E1[SQLite Database]
        E2[Market Data Tables]
        E3[Metadata Tables]
        E4[Indexes & Optimization]
    end
    
    subgraph "External Data Sources"
        F1[Yahoo Finance]
        F2[Alpha Vantage]
        F3[Polygon.io]
        F4[Finnhub]
        F5[FRED]
    end
    
    A1 --> B1
    A2 --> B1
    A3 --> C1
    A4 --> C1
    
    B1 --> D1
    B2 --> B3
    B3 --> B4
    
    C1 --> C2
    C2 --> C3
    C3 --> C4
    
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
    
    D1 --> E1
    D2 --> E2
    D3 --> E3
    E1 --> E4
    
    F1 --> D1
    F2 --> D1
    F3 --> D1
    F4 --> D1
    F5 --> D1
```

### API Architecture
```mermaid
sequenceDiagram
    participant Client
    participant FastAPI as FastAPI Server
    participant Collector as Data Collector
    participant Database as SQLite DB
    participant Yahoo as Yahoo Finance
    participant WebSocket as WebSocket Server
    
    Client->>FastAPI: GET /data/AAPL
    FastAPI->>Database: Query historical data
    Database-->>FastAPI: Return data
    FastAPI-->>Client: JSON response
    
    Client->>FastAPI: GET /realtime/AAPL
    FastAPI->>Yahoo: Fetch current price
    Yahoo-->>FastAPI: Real-time data
    FastAPI-->>Client: Current price data
    
    Client->>WebSocket: Connect & Subscribe
    WebSocket->>Collector: Start real-time collection
    Collector->>Yahoo: Fetch updates
    Yahoo-->>Collector: Price updates
    Collector-->>WebSocket: Stream data
    WebSocket-->>Client: Real-time updates
    
    FastAPI->>Collector: Background task (every 15min)
    Collector->>Yahoo: Bulk data fetch
    Yahoo-->>Collector: Historical data
    Collector->>Database: Store data
```

### Data Flow Architecture
```mermaid
flowchart TD
    subgraph "Data Sources"
        A[Yahoo Finance]
        B[Alpha Vantage]
        C[Polygon.io]
        D[Finnhub]
    end
    
    subgraph "Collection Layer"
        E[Data Fetcher]
        F[Rate Limiter]
        G[Error Handler]
        H[Data Validator]
    end
    
    subgraph "Processing Layer"
        I[Technical Indicators]
        J[Price Analytics]
        K[Volume Analysis]
        L[Market Sentiment]
    end
    
    subgraph "Storage Layer"
        M[(SQLite Database)]
        N[Time Series Tables]
        O[Metadata Tables]
    end
    
    subgraph "API Layer"
        P[RESTful Endpoints]
        Q[WebSocket Streams]
        R[Background Tasks]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    
    E --> F
    F --> G
    G --> H
    
    H --> I
    H --> J
    H --> K
    H --> L
    
    I --> M
    J --> N
    K --> O
    L --> M
    
    M --> P
    N --> Q
    O --> R
```

## 🚀 Features

### 📊 Core API Features
- **📡 Real-time Data Streaming**: WebSocket-based live price feeds with sub-second latency
- **🗄️ High-Performance Storage**: SQLite database with optimized indexing and query performance
- **🔄 Automated Data Collection**: Background tasks with configurable intervals (1min-1day)
- **📊 Advanced Analytics API**: 20+ technical indicators, market sentiment, and statistical metrics
- **🌐 Production-Ready API**: FastAPI with OpenAPI/Swagger docs, CORS, and error handling

### 🔌 Real-time Capabilities
- **WebSocket Streaming**: Multi-symbol real-time price feeds
- **Subscription Management**: Dynamic symbol subscription/unsubscription
- **Multiple Data Types**: Tick data, quotes, trades, and order book updates
- **Connection Management**: Automatic reconnection and heartbeat monitoring
- **Broadcast Modes**: Individual and bulk data broadcasting

### 📊 Data Sources Integration
- **Multi-Source Architecture**: Yahoo Finance, Alpha Vantage, Polygon.io, Finnhub
- **Fallback Mechanisms**: Automatic failover between data providers
- **Rate Limiting**: Built-in API rate limiting and quota management
- **Data Quality Assurance**: Validation, cleansing, and anomaly detection
- **Economic Data**: FRED integration for macroeconomic indicators

### 🚀 Advanced Features
- **Technical Analysis Engine**: RSI, MACD, Bollinger Bands, ATR, and custom indicators
- **Market Sentiment Analysis**: News sentiment aggregation and fear/greed indicators
- **Portfolio Analytics**: Real-time portfolio tracking and performance metrics
- **Historical Backtesting**: Strategy backtesting with performance attribution
- **API Authentication**: JWT tokens and API key management
- **Monitoring & Logging**: Comprehensive request/response logging and metrics

## 🛠️ Installation

```bash
git clone https://github.com/olaitanojo/market-data-api.git
cd market-data-api
pip install fastapi uvicorn pandas numpy yfinance sqlite3
python app.py
```

Visit http://localhost:8000/docs for API documentation.

## 📊 API Endpoints

### Core Data Endpoints
- **GET /**: API overview, health status, and available endpoints
- **GET /symbols**: List of available stock symbols with metadata
- **GET /data/{symbol}**: Historical OHLCV data with query parameters
- **GET /realtime/{symbol}**: Current real-time price and market data
- **GET /quote/{symbol}**: Latest quote with bid/ask spreads

### Analytics Endpoints
- **GET /analytics/{symbol}**: Complete technical analysis with 20+ indicators
- **GET /indicators/{symbol}**: Specific technical indicators (RSI, MACD, etc.)
- **GET /sentiment/{symbol}**: Market sentiment analysis and scores
- **GET /volatility/{symbol}**: Volatility metrics and statistical measures
- **GET /patterns/{symbol}**: Chart pattern recognition and signals

### Portfolio & Management
- **GET /portfolio**: Portfolio performance and risk metrics
- **POST /portfolio/add**: Add symbols to portfolio tracking
- **DELETE /portfolio/{symbol}**: Remove symbol from portfolio
- **GET /watchlist**: User watchlist management

### Data Management
- **POST /collect**: Trigger manual data collection for symbols
- **POST /collect/bulk**: Bulk data collection with progress tracking
- **GET /status/collection**: Data collection status and schedule
- **GET /health**: System health check and metrics

### Query Parameters
- `period`: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
- `interval`: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
- `start_date`: Start date for historical data (YYYY-MM-DD)
- `end_date`: End date for historical data (YYYY-MM-DD)
- `limit`: Maximum number of records to return
- `format`: Response format (json, csv)
- `indicators`: Comma-separated list of technical indicators to include

## 📊 Sample Responses

### Real-time Quote Data
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-12-29T15:30:00Z",
  "price": 175.43,
  "change": 2.15,
  "change_percent": 1.24,
  "volume": 52847392,
  "market_cap": 2847392847392,
  "bid": 175.42,
  "ask": 175.44,
  "bid_size": 100,
  "ask_size": 200
}
```

### Technical Analysis Response
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-12-29T15:30:00Z",
  "indicators": {
    "rsi": 45.32,
    "macd": {
      "value": 1.23,
      "signal": 1.15,
      "histogram": 0.08
    },
    "bollinger_bands": {
      "upper": 178.45,
      "middle": 175.20,
      "lower": 171.95
    },
    "moving_averages": {
      "sma_20": 174.65,
      "sma_50": 172.30,
      "ema_12": 175.80
    }
  },
  "sentiment": {
    "score": 0.15,
    "label": "Positive",
    "confidence": 0.78
  }
}
```

### Historical Data Response
```json
{
  "symbol": "AAPL",
  "data": [
    {
      "timestamp": "2024-12-29T09:30:00Z",
      "open": 173.20,
      "high": 175.80,
      "low": 172.95,
      "close": 175.43,
      "volume": 52847392,
      "adj_close": 175.43
    }
  ],
  "metadata": {
    "total_records": 252,
    "period": "1y",
    "last_updated": "2024-12-29T15:30:00Z"
  }
}
```

## 🎯 Use Cases

### 🤖 Trading & Automation
- **Algorithmic Trading Bots**: Real-time price feeds for automated trading systems
- **High-Frequency Trading**: Sub-second latency data for HFT strategies
- **Options Trading**: Real-time options chain data and Greeks calculations
- **Arbitrage Detection**: Multi-exchange price comparison and opportunity identification

### 📊 Analytics & Research
- **Quantitative Analysis**: Historical data for statistical modeling and backtesting
- **Market Research**: Comprehensive market data for academic and professional research
- **Risk Management**: Real-time portfolio monitoring and risk assessment
- **Performance Attribution**: Detailed performance analysis and reporting

### 📱 Applications & Dashboards
- **Financial Dashboards**: Real-time market data visualization and monitoring
- **Portfolio Management**: Live portfolio tracking and performance metrics
- **Market Surveillance**: Unusual activity detection and alert systems
- **News Integration**: Correlating market movements with news events

### 🏦 Enterprise Solutions
- **Internal APIs**: White-label market data API for financial institutions
- **Compliance Monitoring**: Trade surveillance and regulatory reporting
- **Data Warehousing**: Historical data storage for enterprise analytics
- **Third-party Integration**: API gateway for external financial services

## 🔌 WebSocket Real-time Streaming

### JavaScript/TypeScript Client
```javascript
const ws = new WebSocket('ws://localhost:8765');

// Subscribe to real-time data
ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    symbols: ['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
    data_types: ['tick', 'quote', 'trade'],
    frequency: '1s',
    indicators: ['rsi', 'macd', 'bollinger_bands']
  }));
};

// Handle real-time updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', {
    symbol: data.symbol,
    price: data.price,
    change: data.change_percent,
    volume: data.volume,
    timestamp: data.timestamp
  });
};

// Unsubscribe from specific symbols
ws.send(JSON.stringify({
  action: 'unsubscribe',
  symbols: ['MSFT']
}));
```

### Python WebSocket Client
```python
import asyncio
import websockets
import json

async def market_data_client():
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to symbols
        subscribe_msg = {
            "action": "subscribe",
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "data_types": ["tick", "quote"],
            "frequency": "1s"
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Listen for updates
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Received: {data['symbol']} @ ${data['price']}")
            except websockets.exceptions.ConnectionClosed:
                break

asyncio.run(market_data_client())
```

### Multiple Data Sources
- **Alpha Vantage**: Real-time quotes and historical data
- **Polygon.io**: Professional-grade market data
- **Finnhub**: Financial news and company data
- **FRED**: Economic indicators and macro data
- **Yahoo Finance**: Backup data source

---
Created by [olaitanojo](https://github.com/olaitanojo)
