import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Step 1: Creating Flask app...")
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
import threading

app = Flask(__name__)
CORS(app)
print("OK\n")

print("Step 2: Initializing components...")
from config.settings import get_config
from data.fetcher import DataFetcher
from analysis.market_trend import MarketTrendAnalyzer
from analysis.sector_rotation import SectorRotationAnalyzer
from analysis.capital_flow import CapitalFlowAnalyzer
from analysis.sentiment import SentimentAnalyzer
from signals.generator import SignalGenerator, RiskManager
from screening.selector import StockSelector
from backtest.engine import BacktestEngine

config = get_config()
fetcher = DataFetcher(config)
market_analyzer = MarketTrendAnalyzer(config, fetcher)
sector_analyzer = SectorRotationAnalyzer(config, fetcher)
flow_analyzer = CapitalFlowAnalyzer(config, fetcher)
sentiment_analyzer = SentimentAnalyzer(config, fetcher)
signal_generator = SignalGenerator(config)
risk_manager = RiskManager(config)
print("OK\n")

print("Step 3: Registering routes...")

@app.route('/')
def index():
    return "Hello World"

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/test')
def test():
    return jsonify({"message": "test"})

print("OK\n")

print("Step 4: Starting server...")
try:
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
except Exception as e:
    print(f"Server failed to start: {e}")
    import traceback
    traceback.print_exc()