#!/usr/bin/env python3
"""
Real-time WebSocket Market Data Server
Streams live market data to connected clients with advanced features.

Author: olaitanojo
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, List, Optional, Any
import websockets
from websockets.server import WebSocketServerProtocol
import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import aioredis
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketTick:
    """Market tick data structure"""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class StreamSubscription:
    """Client subscription details"""
    symbols: Set[str]
    data_types: Set[str]  # 'tick', 'bar', 'trade', 'quote'
    frequency: str = "1s"  # Update frequency
    filters: Dict[str, Any] = None

class MarketDataStreamer:
    """Real-time market data streaming service"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.clients: Dict[WebSocketServerProtocol, StreamSubscription] = {}
        self.active_symbols: Set[str] = set()
        self.redis_url = redis_url
        self.redis_client = None
        self.data_cache: Dict[str, MarketTick] = {}
        self.running = False
        
    async def start_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=20
            )
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def stop_redis(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def register_client(self, websocket: WebSocketServerProtocol, subscription: StreamSubscription):
        """Register a new client connection"""
        self.clients[websocket] = subscription
        self.active_symbols.update(subscription.symbols)
        logger.info(f"Client registered for symbols: {subscription.symbols}")
        
        # Send initial data for subscribed symbols
        await self._send_initial_data(websocket, subscription)
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Unregister a client connection"""
        if websocket in self.clients:
            subscription = self.clients.pop(websocket)
            logger.info(f"Client unregistered from symbols: {subscription.symbols}")
            
            # Update active symbols
            self._update_active_symbols()
    
    def _update_active_symbols(self):
        """Update the set of active symbols based on client subscriptions"""
        self.active_symbols = set()
        for subscription in self.clients.values():
            self.active_symbols.update(subscription.symbols)
    
    async def _send_initial_data(self, websocket: WebSocketServerProtocol, subscription: StreamSubscription):
        """Send initial data to newly connected client"""
        try:
            for symbol in subscription.symbols:
                if symbol in self.data_cache:
                    tick = self.data_cache[symbol]
                    message = {
                        'type': 'tick',
                        'data': tick.to_dict()
                    }
                    await websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def fetch_market_data(self, symbol: str) -> Optional[MarketTick]:
        """Fetch real-time market data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get recent data
            hist = ticker.history(period="1d", interval="1m")
            if hist.empty:
                return None
            
            latest = hist.iloc[-1]
            now = datetime.now()
            
            # Get additional real-time info
            info = ticker.info
            previous_close = info.get('previousClose', latest['Close'])
            
            change = latest['Close'] - previous_close
            change_percent = (change / previous_close) * 100 if previous_close else 0
            
            tick = MarketTick(
                symbol=symbol,
                timestamp=now,
                price=latest['Close'],
                volume=int(latest['Volume']),
                change=change,
                change_percent=change_percent,
                bid=info.get('bid'),
                ask=info.get('ask'),
                bid_size=info.get('bidSize'),
                ask_size=info.get('askSize')
            )
            
            # Cache the data
            self.data_cache[symbol] = tick
            
            # Store in Redis if available
            if self.redis_client:
                await self.redis_client.setex(
                    f"market:{symbol}",
                    60,  # 1 minute TTL
                    json.dumps(tick.to_dict())
                )
            
            return tick
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    async def broadcast_tick(self, tick: MarketTick):
        """Broadcast tick data to interested clients"""
        message = {
            'type': 'tick',
            'data': tick.to_dict()
        }
        message_json = json.dumps(message)
        
        # Find clients interested in this symbol
        interested_clients = [
            websocket for websocket, subscription in self.clients.items()
            if tick.symbol in subscription.symbols and 'tick' in subscription.data_types
        ]
        
        # Send to all interested clients
        if interested_clients:
            await asyncio.gather(
                *[self._send_safe(client, message_json) for client in interested_clients],
                return_exceptions=True
            )
    
    async def _send_safe(self, websocket: WebSocketServerProtocol, message: str):
        """Safely send message to websocket"""
        try:
            await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            # Client disconnected, remove from clients
            await self.unregister_client(websocket)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def data_streaming_loop(self):
        """Main data streaming loop"""
        logger.info("Starting market data streaming loop")
        
        while self.running:
            if not self.active_symbols or not self.clients:
                await asyncio.sleep(1)
                continue
            
            # Fetch data for all active symbols
            tasks = [self.fetch_market_data(symbol) for symbol in self.active_symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Broadcast ticks
            for result in results:
                if isinstance(result, MarketTick):
                    await self.broadcast_tick(result)
            
            # Wait before next update (1 second for real-time)
            await asyncio.sleep(1)
    
    async def handle_websocket(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket connections"""
        logger.info(f"New WebSocket connection from {websocket.remote_address}")
        
        try:
            # Wait for subscription message
            subscription_msg = await websocket.recv()
            subscription_data = json.loads(subscription_msg)
            
            # Parse subscription
            subscription = StreamSubscription(
                symbols=set(subscription_data.get('symbols', [])),
                data_types=set(subscription_data.get('data_types', ['tick'])),
                frequency=subscription_data.get('frequency', '1s'),
                filters=subscription_data.get('filters', {})
            )
            
            # Register client
            await self.register_client(websocket, subscription)
            
            # Send confirmation
            await websocket.send(json.dumps({
                'type': 'subscription_confirmed',
                'symbols': list(subscription.symbols),
                'data_types': list(subscription.data_types)
            }))
            
            # Keep connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error handling WebSocket: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle messages from clients"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            # Add symbols to subscription
            new_symbols = set(data.get('symbols', []))
            if websocket in self.clients:
                self.clients[websocket].symbols.update(new_symbols)
                self.active_symbols.update(new_symbols)
                
                # Send confirmation
                await websocket.send(json.dumps({
                    'type': 'subscribe_confirmed',
                    'symbols': list(new_symbols)
                }))
                
        elif message_type == 'unsubscribe':
            # Remove symbols from subscription
            remove_symbols = set(data.get('symbols', []))
            if websocket in self.clients:
                self.clients[websocket].symbols -= remove_symbols
                self._update_active_symbols()
                
                # Send confirmation
                await websocket.send(json.dumps({
                    'type': 'unsubscribe_confirmed',
                    'symbols': list(remove_symbols)
                }))
        
        elif message_type == 'ping':
            # Respond to ping
            await websocket.send(json.dumps({'type': 'pong'}))
    
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start the WebSocket server"""
        self.running = True
        await self.start_redis()
        
        # Start data streaming loop
        streaming_task = asyncio.create_task(self.data_streaming_loop())
        
        # Start WebSocket server
        logger.info(f"Starting WebSocket server on {host}:{port}")
        async with websockets.serve(self.handle_websocket, host, port):
            logger.info("WebSocket server started successfully")
            await streaming_task
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        logger.info("Stopping WebSocket server")
        self.running = False
        await self.stop_redis()

# Enhanced REST API with WebSocket integration
class EnhancedMarketDataAPI:
    """Enhanced API with WebSocket support"""
    
    def __init__(self):
        self.streamer = MarketDataStreamer()
    
    async def start_services(self):
        """Start all services"""
        # Start WebSocket server
        ws_task = asyncio.create_task(
            self.streamer.start_server(host="0.0.0.0", port=8765)
        )
        
        # Start REST API (would integrate with existing FastAPI app)
        logger.info("Enhanced Market Data API services started")
        await ws_task

# WebSocket client example
class MarketDataWebSocketClient:
    """Example WebSocket client for testing"""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.websocket = None
    
    async def connect(self, symbols: List[str], data_types: List[str] = None):
        """Connect to WebSocket server and subscribe"""
        if data_types is None:
            data_types = ['tick']
        
        self.websocket = await websockets.connect(self.uri)
        
        # Send subscription
        subscription = {
            'symbols': symbols,
            'data_types': data_types,
            'frequency': '1s'
        }
        
        await self.websocket.send(json.dumps(subscription))
        
        # Wait for confirmation
        response = await self.websocket.recv()
        confirmation = json.loads(response)
        logger.info(f"Subscription confirmed: {confirmation}")
    
    async def listen(self):
        """Listen for incoming messages"""
        if not self.websocket:
            raise RuntimeError("Not connected to server")
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming messages"""
        message_type = data.get('type')
        
        if message_type == 'tick':
            tick_data = data['data']
            symbol = tick_data['symbol']
            price = tick_data['price']
            change_percent = tick_data.get('change_percent', 0)
            
            logger.info(f"{symbol}: ${price:.2f} ({change_percent:+.2f}%)")
        
        elif message_type == 'subscription_confirmed':
            logger.info(f"Subscribed to: {data.get('symbols')}")
        
        else:
            logger.info(f"Received: {data}")
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()

async def main():
    """Test the WebSocket server"""
    logger.info("Starting Enhanced Market Data API with WebSocket support")
    
    # Start server
    api = EnhancedMarketDataAPI()
    await api.start_services()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
