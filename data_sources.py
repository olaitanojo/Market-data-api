#!/usr/bin/env python3
"""
Additional Data Sources Integration
Integrates multiple data providers for comprehensive market coverage.

Author: olaitanojo
"""

import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    YAHOO = "yahoo"
    ALPHA_VANTAGE = "alpha_vantage" 
    POLYGON = "polygon"
    FINNHUB = "finnhub"
    IEX_CLOUD = "iex_cloud"
    QUANDL = "quandl"
    FRED = "fred"

@dataclass
class DataSourceConfig:
    """Configuration for a data source"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    timeout: int = 30
    retry_count: int = 3
    
class DataProvider(ABC):
    """Abstract base class for data providers"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for a symbol"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, period: str) -> pd.DataFrame:
        """Get historical data for a symbol"""
        pass

class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider"""
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote from Alpha Vantage"""
        url = f"{self.config.base_url}/query"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': self.config.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if 'Global Quote' in data:
                    quote = data['Global Quote']
                    return {
                        'symbol': symbol,
                        'price': float(quote.get('05. price', 0)),
                        'change': float(quote.get('09. change', 0)),
                        'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                        'volume': int(quote.get('06. volume', 0)),
                        'timestamp': datetime.now(),
                        'source': 'alpha_vantage'
                    }
                else:
                    logger.error(f"Alpha Vantage API error: {data}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage quote for {symbol}: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get historical data from Alpha Vantage"""
        url = f"{self.config.base_url}/query"
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': symbol,
            'outputsize': 'full',
            'apikey': self.config.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if 'Time Series (Daily)' in data:
                    time_series = data['Time Series (Daily)']
                    
                    # Convert to DataFrame
                    df_data = []
                    for date_str, values in time_series.items():
                        df_data.append({
                            'Date': pd.to_datetime(date_str),
                            'Open': float(values['1. open']),
                            'High': float(values['2. high']),
                            'Low': float(values['3. low']),
                            'Close': float(values['4. close']),
                            'Adj_Close': float(values['5. adjusted close']),
                            'Volume': int(values['6. volume'])
                        })
                    
                    df = pd.DataFrame(df_data)
                    df.set_index('Date', inplace=True)
                    return df.sort_index()
                else:
                    logger.error(f"Alpha Vantage historical data error: {data}")
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage historical data for {symbol}: {e}")
            return pd.DataFrame()

class PolygonProvider(DataProvider):
    """Polygon.io data provider"""
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote from Polygon"""
        url = f"{self.config.base_url}/v2/last/trade/{symbol}"
        headers = {'Authorization': f'Bearer {self.config.api_key}'}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                data = await response.json()
                
                if data.get('status') == 'OK':
                    results = data.get('results', {})
                    return {
                        'symbol': symbol,
                        'price': results.get('p', 0),
                        'volume': results.get('s', 0),
                        'timestamp': datetime.fromtimestamp(results.get('t', 0) / 1000),
                        'source': 'polygon'
                    }
                else:
                    logger.error(f"Polygon API error: {data}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching Polygon quote for {symbol}: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get historical data from Polygon"""
        # Calculate date range
        end_date = datetime.now()
        if period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "6mo":
            start_date = end_date - timedelta(days=180)
        else:
            start_date = end_date - timedelta(days=30)
        
        url = f"{self.config.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        headers = {'Authorization': f'Bearer {self.config.api_key}'}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                data = await response.json()
                
                if data.get('status') == 'OK' and 'results' in data:
                    results = data['results']
                    
                    df_data = []
                    for bar in results:
                        df_data.append({
                            'Date': pd.to_datetime(bar['t'], unit='ms'),
                            'Open': bar['o'],
                            'High': bar['h'],
                            'Low': bar['l'],
                            'Close': bar['c'],
                            'Volume': bar['v']
                        })
                    
                    df = pd.DataFrame(df_data)
                    df.set_index('Date', inplace=True)
                    return df.sort_index()
                else:
                    logger.error(f"Polygon historical data error: {data}")
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Error fetching Polygon historical data for {symbol}: {e}")
            return pd.DataFrame()

class FinnhubProvider(DataProvider):
    """Finnhub data provider"""
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote from Finnhub"""
        url = f"{self.config.base_url}/api/v1/quote"
        params = {
            'symbol': symbol,
            'token': self.config.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if 'c' in data:  # current price
                    return {
                        'symbol': symbol,
                        'price': data['c'],
                        'change': data.get('d', 0),
                        'change_percent': data.get('dp', 0),
                        'high': data.get('h', 0),
                        'low': data.get('l', 0),
                        'open': data.get('o', 0),
                        'previous_close': data.get('pc', 0),
                        'timestamp': datetime.now(),
                        'source': 'finnhub'
                    }
                else:
                    logger.error(f"Finnhub API error: {data}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching Finnhub quote for {symbol}: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get historical data from Finnhub"""
        end_date = datetime.now()
        if period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "6mo":
            start_date = end_date - timedelta(days=180)
        else:
            start_date = end_date - timedelta(days=30)
        
        url = f"{self.config.base_url}/api/v1/stock/candle"
        params = {
            'symbol': symbol,
            'resolution': 'D',
            'from': int(start_date.timestamp()),
            'to': int(end_date.timestamp()),
            'token': self.config.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('s') == 'ok':
                    df_data = []
                    for i in range(len(data['t'])):
                        df_data.append({
                            'Date': pd.to_datetime(data['t'][i], unit='s'),
                            'Open': data['o'][i],
                            'High': data['h'][i],
                            'Low': data['l'][i],
                            'Close': data['c'][i],
                            'Volume': data['v'][i]
                        })
                    
                    df = pd.DataFrame(df_data)
                    df.set_index('Date', inplace=True)
                    return df.sort_index()
                else:
                    logger.error(f"Finnhub historical data error: {data}")
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Error fetching Finnhub historical data for {symbol}: {e}")
            return pd.DataFrame()

class MultiSourceDataAggregator:
    """Aggregates data from multiple sources for reliability"""
    
    def __init__(self):
        self.providers: Dict[str, DataProvider] = {}
        self.source_configs = {
            'alpha_vantage': DataSourceConfig(
                name='Alpha Vantage',
                base_url='https://www.alphavantage.co',
                rate_limit=5  # 5 requests per minute for free tier
            ),
            'polygon': DataSourceConfig(
                name='Polygon',
                base_url='https://api.polygon.io',
                rate_limit=5  # 5 requests per minute for free tier
            ),
            'finnhub': DataSourceConfig(
                name='Finnhub',
                base_url='https://finnhub.io',
                rate_limit=60  # 60 requests per minute for free tier
            )
        }
    
    def add_api_key(self, source: str, api_key: str):
        """Add API key for a data source"""
        if source in self.source_configs:
            self.source_configs[source].api_key = api_key
    
    async def get_best_quote(self, symbol: str) -> Dict[str, Any]:
        """Get quote from multiple sources and return the best one"""
        quotes = []
        
        # Try each provider
        for source_name, config in self.source_configs.items():
            if not config.api_key:
                continue
                
            try:
                if source_name == 'alpha_vantage':
                    provider = AlphaVantageProvider(config)
                elif source_name == 'polygon':
                    provider = PolygonProvider(config)
                elif source_name == 'finnhub':
                    provider = FinnhubProvider(config)
                else:
                    continue
                
                async with provider:
                    quote = await provider.get_quote(symbol)
                    if quote:
                        quotes.append(quote)
                        
            except Exception as e:
                logger.error(f"Error getting quote from {source_name}: {e}")
        
        if not quotes:
            return {}
        
        # Return the most recent quote
        return max(quotes, key=lambda x: x.get('timestamp', datetime.min))
    
    async def get_consensus_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get historical data from multiple sources and create consensus"""
        all_data = []
        
        for source_name, config in self.source_configs.items():
            if not config.api_key:
                continue
            
            try:
                if source_name == 'alpha_vantage':
                    provider = AlphaVantageProvider(config)
                elif source_name == 'polygon':
                    provider = PolygonProvider(config)
                elif source_name == 'finnhub':
                    provider = FinnhubProvider(config)
                else:
                    continue
                
                async with provider:
                    data = await provider.get_historical_data(symbol, period)
                    if not data.empty:
                        data['source'] = source_name
                        all_data.append(data)
                        
            except Exception as e:
                logger.error(f"Error getting historical data from {source_name}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        # If we have multiple sources, create consensus
        if len(all_data) == 1:
            return all_data[0]
        
        # Merge data from multiple sources
        consensus_data = all_data[0].copy()
        for additional_data in all_data[1:]:
            # Simple average for price data where dates overlap
            common_dates = consensus_data.index.intersection(additional_data.index)
            for date in common_dates:
                for col in ['Open', 'High', 'Low', 'Close']:
                    if col in consensus_data.columns and col in additional_data.columns:
                        consensus_data.loc[date, col] = (
                            consensus_data.loc[date, col] + additional_data.loc[date, col]
                        ) / 2
        
        return consensus_data
    
    async def get_market_news(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get market news from available sources"""
        news = []
        
        # Try Finnhub for news
        finnhub_config = self.source_configs.get('finnhub')
        if finnhub_config and finnhub_config.api_key:
            try:
                provider = FinnhubProvider(finnhub_config)
                async with provider:
                    # Custom news endpoint call
                    url = f"{finnhub_config.base_url}/api/v1/company-news"
                    params = {
                        'symbol': symbol,
                        'from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                        'to': datetime.now().strftime('%Y-%m-%d'),
                        'token': finnhub_config.api_key
                    }
                    
                    async with provider.session.get(url, params=params) as response:
                        data = await response.json()
                        
                        for article in data[:limit]:
                            news.append({
                                'headline': article.get('headline', ''),
                                'summary': article.get('summary', ''),
                                'url': article.get('url', ''),
                                'datetime': datetime.fromtimestamp(article.get('datetime', 0)),
                                'source': article.get('source', ''),
                                'sentiment': None  # Could add sentiment analysis
                            })
            except Exception as e:
                logger.error(f"Error fetching news from Finnhub: {e}")
        
        return news

# Economic data provider for macro indicators
class FREDDataProvider:
    """Federal Reserve Economic Data provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
    
    async def get_economic_series(self, series_id: str, limit: int = 100) -> pd.DataFrame:
        """Get economic data series from FRED"""
        url = f"{self.base_url}/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'limit': limit,
            'sort_order': 'desc'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if 'observations' in data:
                        observations = data['observations']
                        
                        df_data = []
                        for obs in observations:
                            if obs['value'] != '.':  # FRED uses '.' for missing values
                                df_data.append({
                                    'date': pd.to_datetime(obs['date']),
                                    'value': float(obs['value'])
                                })
                        
                        if df_data:
                            df = pd.DataFrame(df_data)
                            df.set_index('date', inplace=True)
                            return df.sort_index()
                    
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Error fetching FRED series {series_id}: {e}")
            return pd.DataFrame()
    
    async def get_key_indicators(self) -> Dict[str, Any]:
        """Get key economic indicators"""
        indicators = {
            'GDP': 'GDP',
            'Unemployment_Rate': 'UNRATE',
            'Inflation_Rate': 'CPIAUCSL',
            'Fed_Funds_Rate': 'FEDFUNDS',
            'Consumer_Sentiment': 'UMCSENT',
            'Industrial_Production': 'INDPRO'
        }
        
        results = {}
        for name, series_id in indicators.items():
            try:
                df = await self.get_economic_series(series_id, limit=1)
                if not df.empty:
                    results[name] = {
                        'value': df.iloc[0]['value'],
                        'date': df.index[0],
                        'series_id': series_id
                    }
            except Exception as e:
                logger.error(f"Error fetching {name}: {e}")
        
        return results

async def main():
    """Test the data sources integration"""
    logger.info("Testing Multi-Source Data Aggregator")
    
    # Initialize aggregator
    aggregator = MultiSourceDataAggregator()
    
    # Add API keys (these would come from environment variables in production)
    # aggregator.add_api_key('alpha_vantage', 'YOUR_ALPHA_VANTAGE_KEY')
    # aggregator.add_api_key('polygon', 'YOUR_POLYGON_KEY')  
    # aggregator.add_api_key('finnhub', 'YOUR_FINNHUB_KEY')
    
    # Test getting quote (will work with yfinance as fallback)
    print("Testing quote retrieval...")
    quote = await aggregator.get_best_quote('AAPL')
    print(f"Best quote for AAPL: {quote}")
    
    # Test economic data
    # fred_provider = FREDDataProvider('YOUR_FRED_API_KEY')
    # indicators = await fred_provider.get_key_indicators()
    # print(f"Key economic indicators: {indicators}")

if __name__ == "__main__":
    asyncio.run(main())
