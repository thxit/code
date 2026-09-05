import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Test 1: Basic Flask")
from flask import Flask, render_template, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
print("OK\n")

print("Test 2: ThreadPoolExecutor")
from concurrent.futures import ThreadPoolExecutor
_executor = ThreadPoolExecutor(max_workers=8)
print("OK\n")

print("Test 3: Settings")
from config.settings import get_config
config = get_config()
print("OK\n")

print("Test 4: DataFetcher")
from data.fetcher import DataFetcher
fetcher = DataFetcher(config)
print("OK\n")

print("Test 5: MarketTrendAnalyzer")
from analysis.market_trend import MarketTrendAnalyzer
market_analyzer = MarketTrendAnalyzer(config, fetcher)
print("OK\n")

print("Test 6: SectorRotationAnalyzer")
from analysis.sector_rotation import SectorRotationAnalyzer
sector_analyzer = SectorRotationAnalyzer(config, fetcher)
print("OK\n")

print("Test 7: CapitalFlowAnalyzer")
from analysis.capital_flow import CapitalFlowAnalyzer
flow_analyzer = CapitalFlowAnalyzer(config, fetcher)
print("OK\n")

print("Test 8: SentimentAnalyzer")
from analysis.sentiment import SentimentAnalyzer
sentiment_analyzer = SentimentAnalyzer(config, fetcher)
print("OK\n")

print("Test 9: SignalGenerator and RiskManager")
from signals.generator import SignalGenerator, RiskManager
signal_generator = SignalGenerator(config)
risk_manager = RiskManager(config)
print("OK\n")

print("Test 10: StockSelector")
from screening.selector import StockSelector
print("OK\n")

print("Test 11: BacktestEngine")
from backtest.engine import BacktestEngine
print("OK\n")

print("All modules imported successfully!")