import sys
import os
import json
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from waitress import serve
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 延迟初始化组件
_fetcher = None
_market_analyzer = None
_sector_analyzer = None
_flow_analyzer = None
_sentiment_analyzer = None
_signal_generator = None
_risk_manager = None

_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 120

def init_components():
    global _fetcher, _market_analyzer, _sector_analyzer, _flow_analyzer
    global _sentiment_analyzer, _signal_generator, _risk_manager
    
    if _fetcher is not None:
        return
    
    from config.settings import get_config
    from data.fetcher import DataFetcher
    from analysis.market_trend import MarketTrendAnalyzer
    from analysis.sector_rotation import SectorRotationAnalyzer
    from analysis.capital_flow import CapitalFlowAnalyzer
    from analysis.sentiment import SentimentAnalyzer
    from signals.generator import SignalGenerator, RiskManager
    
    config = get_config()
    _fetcher = DataFetcher(config)
    _market_analyzer = MarketTrendAnalyzer(config, _fetcher)
    _sector_analyzer = SectorRotationAnalyzer(config, _fetcher)
    _flow_analyzer = CapitalFlowAnalyzer(config, _fetcher)
    _sentiment_analyzer = SentimentAnalyzer(config, _fetcher)
    _signal_generator = SignalGenerator(config)
    _risk_manager = RiskManager(config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

@app.route('/api/quick')
def api_quick():
    init_components()
    
    try:
        market_trend = _market_analyzer.analyze("000001", period=120)
        sentiment = _sentiment_analyzer.analyze()
        capital_flow = _flow_analyzer.analyze()
        
        signal = _signal_generator.generate(
            market_trend, {"rotation_signal": {}, "top_sectors": []},
            capital_flow, sentiment,
        )
        
        return jsonify({
            "meta": {"analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": "quick"},
            "market_trend": market_trend,
            "sentiment": sentiment,
            "capital_flow": capital_flow,
            "trading_signal": {
                "action": signal.action, "strength": signal.strength,
                "score": signal.score, "reasons": signal.reasons,
                "warnings": signal.warnings,
            },
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()[:2000]}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    init_components()
    mode = request.json.get("mode", "full") if request.is_json else "full"
    
    try:
        market_trend = _market_analyzer.analyze("000001", period=250)
        sentiment = _sentiment_analyzer.analyze()
        capital_flow = _flow_analyzer.analyze()
        
        result = {
            "meta": {"analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": mode},
            "market_trend": market_trend,
            "sentiment": sentiment,
            "capital_flow": capital_flow,
        }
        
        if mode == "full":
            sector_rotation = _sector_analyzer.analyze(period=20)
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
            
            from screening.selector import StockSelector
            selector = StockSelector(lambda: _fetcher.fetch_stock_list())
            result["recommended_stocks"] = selector.screen(top_n=20)
            
            from config.settings import get_config
            from backtest.engine import BacktestEngine
            engine = BacktestEngine(get_config(), _fetcher)
            bt = engine.run("000001", period=500)
            result["backtest"] = {
                "total_return": bt.total_return, "annual_return": bt.annual_return,
                "sharpe_ratio": bt.sharpe_ratio, "max_drawdown": bt.max_drawdown,
                "win_rate": bt.win_rate, "total_trades": bt.total_trades,
                "profit_factor": bt.profit_factor,
                "avg_profit": bt.avg_profit, "avg_loss": bt.avg_loss,
                "winning_trades": bt.winning_trades, "losing_trades": bt.losing_trades,
            }
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
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()[:2000]}), 500

@app.route('/api/screen-stocks')
def screen_stocks():
    init_components()
    strategy = request.args.get('strategy', 'breakout')
    top_n = int(request.args.get('top_n', 20))
    
    try:
        from screening.selector import StockSelector
        selector = StockSelector(lambda: _fetcher.fetch_stock_list())
        stocks = selector.screen(strategy=strategy, top_n=top_n)
        return jsonify(stocks)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()[:2000]}), 500

@app.route('/api/market-trend')
def api_market_trend():
    init_components()
    try:
        result = _market_analyzer.analyze("000001", period=250)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()[:2000]}), 500

@app.route('/api/sector-rotation')
def api_sector_rotation():
    init_components()
    try:
        result = _sector_analyzer.analyze(period=20)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()[:2000]}), 500

@app.route('/api/capital-flow')
def api_capital_flow():
    init_components()
    try:
        result = _flow_analyzer.analyze()
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()[:2000]}), 500

@app.route('/api/sentiment')
def api_sentiment():
    init_components()
    try:
        result = _sentiment_analyzer.analyze()
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()[:2000]}), 500

if __name__ == '__main__':
    print("Starting A股量化交易系统...")
    print("Running on http://127.0.0.1:5000")
    serve(app, host='127.0.0.1', port=5000, threads=4)