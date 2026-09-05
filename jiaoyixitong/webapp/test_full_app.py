import sys
import os
import json
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Importing modules...")
from config.settings import get_config
from data.fetcher import DataFetcher
from analysis.market_trend import MarketTrendAnalyzer
from analysis.sector_rotation import SectorRotationAnalyzer
from analysis.capital_flow import CapitalFlowAnalyzer
from analysis.sentiment import SentimentAnalyzer
from signals.generator import SignalGenerator, RiskManager
from screening.selector import StockSelector
from backtest.engine import BacktestEngine

print("Creating app...")
app = Flask(__name__)
CORS(app)

print("Initializing components...")
config = get_config()
fetcher = DataFetcher(config)
market_analyzer = MarketTrendAnalyzer(config, fetcher)
sector_analyzer = SectorRotationAnalyzer(config, fetcher)
flow_analyzer = CapitalFlowAnalyzer(config, fetcher)
sentiment_analyzer = SentimentAnalyzer(config, fetcher)
signal_generator = SignalGenerator(config)
risk_manager = RiskManager(config)

_cache = {}
_cache_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=8)
CACHE_TTL = 120

print("Registering routes...")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

@app.route('/api/quick')
def quick_analysis():
    result = {"meta": {"analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": "quick"}}
    
    def fetch_market():
        return market_analyzer.analyze("000001", period=250)
    
    def fetch_flow():
        return flow_analyzer.analyze()
    
    def fetch_sentiment():
        return sentiment_analyzer.analyze()
    
    futures = {
        'market': _executor.submit(fetch_market),
        'flow': _executor.submit(fetch_flow),
        'sentiment': _executor.submit(fetch_sentiment)
    }
    
    try:
        market_trend = futures['market'].result(timeout=60)
        result["market_trend"] = market_trend
        capital_flow = futures['flow'].result(timeout=60)
        result["capital_flow"] = capital_flow
        sentiment = futures['sentiment'].result(timeout=60)
        result["sentiment"] = sentiment
        
        signal = signal_generator.generate(
            market_trend, {"rotation_signal": {}, "top_sectors": []},
            capital_flow, sentiment,
        )
        result["trading_signal"] = {
            "action": signal.action, "strength": signal.strength,
            "score": signal.score, "reasons": signal.reasons,
            "warnings": signal.warnings,
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

print("Starting server...")
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)