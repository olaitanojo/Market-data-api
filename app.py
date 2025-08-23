#!/usr/bin/env python3
"""
Market Data Scraper & API
A comprehensive market data collection, storage, and API system with real-time capabilities.

Author: olaitanojo
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import asyncio
import aiohttp
from typing import List, Dict, Optional
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_PATH = "market_data.db"

class StockData(BaseModel):
    """Stock data model"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None

class MarketDataRequest(BaseModel):
    """Request model for market data"""
    symbols: List[str]
    period: str = "1d"
    interval: str = "1m"

class DataCollector:
    """Data collection and storage manager"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create stock data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                adj_close REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp)
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
            ON stock_data(symbol, timestamp)
        """)
        
        # Create market metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_metadata (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def store_stock_data(self, symbol: str, data: pd.DataFrame):
        """Store stock data in database"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Prepare data for insertion
            data_records = []
            for timestamp, row in data.iterrows():
                record = (
                    symbol,
                    timestamp,
                    row.get('Open', 0),
                    row.get('High', 0),
                    row.get('Low', 0),
                    row.get('Close', 0),
                    row.get('Volume', 0),
                    row.get('Adj Close', row.get('Close', 0))
                )
                data_records.append(record)
            
            # Insert data with conflict resolution
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO stock_data 
                (symbol, timestamp, open, high, low, close, volume, adj_close)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data_records)
            
            conn.commit()
            logger.info(f"Stored {len(data_records)} records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error storing data for {symbol}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_stock_data(self, symbol: str, start_date: str = None, 
                      end_date: str = None, limit: int = 1000) -> pd.DataFrame:
        """Retrieve stock data from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM stock_data WHERE symbol = ?"
        params = [symbol]
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            df = pd.read_sql_query(query, conn, params=params)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            logger.error(f"Error retrieving data for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def fetch_and_store_data(self, symbols: List[str], period: str = "1d"):
        """Fetch data from Yahoo Finance and store in database"""
        for symbol in symbols:
            try:
                logger.info(f"Fetching data for {symbol}")
                ticker = yf.Ticker(symbol)
                
                # Get historical data
                hist_data = ticker.history(period=period)
                if not hist_data.empty:
                    self.store_stock_data(symbol, hist_data)
                
                # Get company info for metadata
                try:
                    info = ticker.info
                    self.store_metadata(symbol, info)
                except:
                    pass  # Metadata is optional
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
    
    def store_metadata(self, symbol: str, info: Dict):
        """Store company metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO market_metadata
                (symbol, company_name, sector, industry, market_cap)
                VALUES (?, ?, ?, ?, ?)
            """, (
                symbol,
                info.get('longName', ''),
                info.get('sector', ''),
                info.get('industry', ''),
                info.get('marketCap', 0)
            ))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error storing metadata for {symbol}: {e}")
        finally:
            conn.close()
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT symbol FROM stock_data ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return symbols

# Global data collector instance
data_collector = DataCollector()

# Background data collection task
async def periodic_data_collection():
    """Periodically collect data for popular stocks"""
    popular_stocks = [
        'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
        'SPY', 'QQQ', 'IWM', 'GLD', 'SLV', '^SPX', '^VIX'
    ]
    
    while True:
        try:
            logger.info("Starting periodic data collection...")
            data_collector.fetch_and_store_data(popular_stocks, period="1d")
            logger.info("Periodic data collection completed")
            
            # Wait 15 minutes before next collection
            await asyncio.sleep(900)
            
        except Exception as e:
            logger.error(f"Error in periodic collection: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Market Data API...")
    
    # Start background data collection
    asyncio.create_task(periodic_data_collection())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Market Data API...")

# FastAPI app
app = FastAPI(
    title="Market Data API",
    description="Real-time market data collection and API service",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Market Data API",
        "version": "1.0.0",
        "endpoints": [
            "/docs",
            "/symbols",
            "/data/{symbol}",
            "/collect",
            "/realtime/{symbol}",
            "/analytics/{symbol}"
        ]
    }

@app.get("/symbols")
async def get_symbols():
    """Get list of available symbols"""
    symbols = data_collector.get_available_symbols()
    return {"symbols": symbols, "count": len(symbols)}

@app.get("/data/{symbol}")
async def get_stock_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
):
    """Get historical stock data"""
    
    # Validate symbol
    symbol = symbol.upper()
    
    # Get data from database
    df = data_collector.get_stock_data(symbol, start_date, end_date, limit)
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
    
    # Convert to JSON-friendly format
    data = []
    for _, row in df.iterrows():
        data.append({
            "timestamp": row['timestamp'].isoformat(),
            "open": row['open'],
            "high": row['high'],
            "low": row['low'],
            "close": row['close'],
            "volume": row['volume'],
            "adj_close": row['adj_close']
        })
    
    return {
        "symbol": symbol,
        "data": data,
        "count": len(data)
    }

@app.post("/collect")
async def collect_data(request: MarketDataRequest, background_tasks: BackgroundTasks):
    """Manually trigger data collection for specific symbols"""
    
    # Add to background tasks to avoid timeout
    background_tasks.add_task(
        data_collector.fetch_and_store_data,
        request.symbols,
        request.period
    )
    
    return {
        "message": f"Data collection initiated for {len(request.symbols)} symbols",
        "symbols": request.symbols,
        "period": request.period
    }

@app.get("/realtime/{symbol}")
async def get_realtime_data(symbol: str):
    """Get real-time stock data"""
    
    symbol = symbol.upper()
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Get real-time price
        hist = ticker.history(period="1d", interval="1m")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No real-time data for {symbol}")
        
        latest = hist.iloc[-1]
        
        # Get additional info
        info = ticker.info
        
        return {
            "symbol": symbol,
            "timestamp": hist.index[-1].isoformat(),
            "price": latest['Close'],
            "open": latest['Open'],
            "high": latest['High'],
            "low": latest['Low'],
            "volume": latest['Volume'],
            "previous_close": info.get('previousClose', 0),
            "change": latest['Close'] - info.get('previousClose', latest['Close']),
            "change_percent": ((latest['Close'] - info.get('previousClose', latest['Close'])) / 
                             info.get('previousClose', latest['Close'])) * 100 if info.get('previousClose') else 0,
            "market_cap": info.get('marketCap', 0),
            "pe_ratio": info.get('trailingPE', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching real-time data: {str(e)}")

@app.get("/analytics/{symbol}")
async def get_analytics(symbol: str, period: int = 30):
    """Get analytical metrics for a symbol"""
    
    symbol = symbol.upper()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    # Get historical data
    df = data_collector.get_stock_data(
        symbol,
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        limit=1000
    )
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    
    # Calculate analytics
    df = df.sort_values('timestamp')
    df['returns'] = df['close'].pct_change()
    
    analytics = {
        "symbol": symbol,
        "period_days": period,
        "data_points": len(df),
        "price_current": df['close'].iloc[-1],
        "price_high": df['high'].max(),
        "price_low": df['low'].min(),
        "price_avg": df['close'].mean(),
        "volume_avg": df['volume'].mean(),
        "volatility": df['returns'].std() * np.sqrt(252),  # Annualized volatility
        "returns_total": (df['close'].iloc[-1] / df['close'].iloc[0] - 1) if len(df) > 1 else 0,
        "returns_daily_avg": df['returns'].mean(),
        "max_daily_gain": df['returns'].max(),
        "max_daily_loss": df['returns'].min(),
        "positive_days": len(df[df['returns'] > 0]),
        "negative_days": len(df[df['returns'] < 0])
    }
    
    # Calculate moving averages
    if len(df) >= 20:
        analytics["sma_20"] = df['close'].rolling(window=20).mean().iloc[-1]
        analytics["price_vs_sma20"] = (df['close'].iloc[-1] / analytics["sma_20"] - 1) * 100
    
    if len(df) >= 50:
        analytics["sma_50"] = df['close'].rolling(window=50).mean().iloc[-1]
        analytics["price_vs_sma50"] = (df['close'].iloc[-1] / analytics["sma_50"] - 1) * 100
    
    # Calculate RSI
    if len(df) >= 14:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        analytics["rsi"] = rsi.iloc[-1]
    
    return analytics

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "symbols_available": len(data_collector.get_available_symbols())
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
