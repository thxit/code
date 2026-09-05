import sys
import os
import json
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor

print(f"Python path: {sys.path[:3]}")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

_fetcher = None
_market_analyzer = None
_sector_analyzer = None
_flow_analyzer = None
_sentiment_analyzer = None
_signal_generator = None
_risk_manager = None

_cache = {}
_cache_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=8)
CACHE_TTL = 120

def init_components():
    global _fetcher, _market_analyzer, _sector_analyzer, _flow_analyzer
    global _sentiment_analyzer, _signal_generator, _risk_manager
    
    if _fetcher is not None:
        return
    
    print("Initializing components...")
    
    try:
        from config.settings import get_config
        print("  - settings imported")
        config = get_config()
        print("  - config loaded")
        
        from data.fetcher import DataFetcher
        print("  - fetcher imported")
        _fetcher = DataFetcher(config)
        print("  - fetcher created")
        
        from analysis.market_trend import MarketTrendAnalyzer
        print("  - market_trend imported")
        _market_analyzer = MarketTrendAnalyzer(config, _fetcher)
        print("  - market_analyzer created")
        
        from analysis.sector_rotation import SectorRotationAnalyzer
        print("  - sector_rotation imported")
        _sector_analyzer = SectorRotationAnalyzer(config, _fetcher)
        print("  - sector_analyzer created")
        
        from analysis.capital_flow import CapitalFlowAnalyzer
        print("  - capital_flow imported")
        _flow_analyzer = CapitalFlowAnalyzer(config, _fetcher)
        print("  - flow_analyzer created")
        
        from analysis.sentiment import SentimentAnalyzer
        print("  - sentiment imported")
        _sentiment_analyzer = SentimentAnalyzer(config, _fetcher)
        print("  - sentiment_analyzer created")
        
        from signals.generator import SignalGenerator, RiskManager
        print("  - signals imported")
        _signal_generator = SignalGenerator(config)
        print("  - signal_generator created")
        _risk_manager = RiskManager(config)
        print("  - risk_manager created")
        
        print("Components initialized successfully!")
    except Exception as e:
        print(f"Error initializing components: {e}")
        import traceback
        traceback.print_exc()
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

@app.route('/api/quick')
def quick_analysis():
    init_components()
    result = {"meta": {"analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": "quick"}}
    
    def fetch_market():
        return _market_analyzer.analyze("000001", period=250)
    
    def fetch_flow():
        return _flow_analyzer.analyze()
    
    def fetch_sentiment():
        return _sentiment_analyzer.analyze()
    
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
        
        signal = _signal_generator.generate(
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

@app.route('/api/analyze', methods=['POST'])
def analyze():
    init_components()
    mode = request.json.get("mode", "full") if request.is_json else "full"
    result = {"meta": {"analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": mode}}
    
    def fetch_market():
        return _market_analyzer.analyze("000001", period=250)
    
    def fetch_flow():
        return _flow_analyzer.analyze()
    
    def fetch_sentiment():
        return _sentiment_analyzer.analyze()
    
    futures = {
        'market': _executor.submit(fetch_market),
        'flow': _executor.submit(fetch_flow),
        'sentiment': _executor.submit(fetch_sentiment)
    }
    
    if mode == "full":
        def fetch_sector():
            return _sector_analyzer.analyze(period=20)
        futures['sector'] = _executor.submit(fetch_sector)
    
    try:
        market_trend = futures['market'].result(timeout=60)
        result["market_trend"] = market_trend
        capital_flow = futures['flow'].result(timeout=60)
        result["capital_flow"] = capital_flow
        sentiment = futures['sentiment'].result(timeout=60)
        result["sentiment"] = sentiment
        
        if mode == "full":
            sector_rotation = futures['sector'].result(timeout=60)
            result["sector_rotation"] = sector_rotation
            
            signal = _signal_generator.generate(market_trend, sector_rotation, capital_flow, sentiment)
            risk = _risk_manager.evaluate_risk(market_trend, signal)
            
            result["trading_signal"] = {
                "action": signal.action, "strength": signal.strength,
                "score": signal.score, "reasons": signal.reasons,
                "warnings": signal.warnings, "position_advice": signal.position_advice,
                "stop_loss": signal.stop_loss, "take_profit": signal.take_profit,
            }
            result["risk_assessment"] = risk
        else:
            signal = _signal_generator.generate(
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

@app.route('/api/screen-stocks')
def screen_stocks():
    init_components()
    strategy = request.args.get('strategy', 'breakout')
    top_n = int(request.args.get('top_n', 20))
    
    from screening.selector import StockSelector
    selector = StockSelector(lambda: _fetcher.fetch_stock_list())
    stocks = selector.screen(strategy=strategy, top_n=top_n)
    return jsonify(stocks)

if __name__ == "__main__":
    print("Starting A股量化交易系统...")
    print("Running on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)