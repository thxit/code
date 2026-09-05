import sys
import os
import json
import threading
import asyncio
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemConfig, get_config
from data.fetcher import DataFetcher
from analysis.market_trend import MarketTrendAnalyzer
from analysis.sector_rotation import SectorRotationAnalyzer
from analysis.capital_flow import CapitalFlowAnalyzer
from analysis.sentiment import SentimentAnalyzer
from signals.generator import SignalGenerator, RiskManager
from screening.selector import StockSelector
from backtest.engine import BacktestEngine

app = Flask(__name__)
CORS(app)

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

# 缓存时间（秒）
CACHE_TTL = 120  # 2分钟


def get_cached_data(key):
    with _cache_lock:
        item = _cache.get(key)
        if item and (datetime.now().timestamp() - item['timestamp']) < CACHE_TTL:
            return item['data']
        return None


def set_cached_data(key, data):
    with _cache_lock:
        _cache[key] = {'timestamp': datetime.now().timestamp(), 'data': data}


def clear_cache():
    with _cache_lock:
        _cache.clear()


@app.route("/")
def index():
    return render_template("index.html")


def _run_analysis_async(mode):
    """异步并行执行分析任务"""
    result = {"meta": {"analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": mode}}

    def fetch_market():
        return market_analyzer.analyze("000001", period=250)

    def fetch_sector():
        return sector_analyzer.analyze(period=20)

    def fetch_flow():
        return flow_analyzer.analyze()

    def fetch_sentiment():
        return sentiment_analyzer.analyze()

    def fetch_stocks():
        selector = StockSelector(lambda: fetcher.fetch_stock_list())
        return selector.screen(top_n=20)

    def fetch_backtest():
        engine = BacktestEngine(config, fetcher)
        return engine.run("000001", period=500)

    # 并行执行获取任务
    futures = {}
    
    # 基础任务（快速模式也需要）
    futures['market'] = _executor.submit(fetch_market)
    futures['flow'] = _executor.submit(fetch_flow)
    futures['sentiment'] = _executor.submit(fetch_sentiment)

    if mode == "full":
        futures['sector'] = _executor.submit(fetch_sector)

    # 获取基础结果
    market_trend = futures['market'].result(timeout=60)
    result["market_trend"] = market_trend
    capital_flow = futures['flow'].result(timeout=60)
    result["capital_flow"] = capital_flow
    sentiment = futures['sentiment'].result(timeout=60)
    result["sentiment"] = sentiment

    if mode == "full":
        sector_rotation = futures['sector'].result(timeout=60)
        result["sector_rotation"] = sector_rotation

        signal = signal_generator.generate(market_trend, sector_rotation, capital_flow, sentiment)
        risk = risk_manager.evaluate_risk(market_trend, signal)

        result["trading_signal"] = {
            "action": signal.action, "strength": signal.strength,
            "score": signal.score, "reasons": signal.reasons,
            "warnings": signal.warnings, "position_advice": signal.position_advice,
            "stop_loss": signal.stop_loss, "take_profit": signal.take_profit,
        }
        result["risk_assessment"] = risk

        stocks = fetch_stocks()
        result["recommended_stocks"] = stocks

        bt = fetch_backtest()
        result["backtest"] = {
            "total_return": bt.total_return, "annual_return": bt.annual_return,
            "sharpe_ratio": bt.sharpe_ratio, "max_drawdown": bt.max_drawdown,
            "win_rate": bt.win_rate, "total_trades": bt.total_trades,
            "profit_factor": bt.profit_factor,
            "avg_profit": bt.avg_profit, "avg_loss": bt.avg_loss,
            "winning_trades": bt.winning_trades, "losing_trades": bt.losing_trades,
        }
    else:
        signal = signal_generator.generate(
            market_trend, {"rotation_signal": {}, "top_sectors": []},
            capital_flow, sentiment,
        )
        result["trading_signal"] = {
            "action": signal.action, "strength": signal.strength,
            "score": signal.score, "reasons": signal.reasons,
            "warnings": signal.warnings,
        }

    return result


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        mode = request.json.get("mode", "full") if request.is_json else "full"
        clear_cache()
        result = _run_analysis_async(mode)
        return jsonify(result)
    except Exception as e:
        import traceback
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc()[:2000],
            "time": datetime.now().isoformat()
        }
        return jsonify(error_info), 500


@app.route("/api/market-trend")
def api_market_trend():
    cached = get_cached_data('market_trend')
    if cached:
        return jsonify(cached)
    result = market_analyzer.analyze("000001", period=250)
    set_cached_data('market_trend', result)
    return jsonify(result)


@app.route("/api/sector-rotation")
def api_sector_rotation():
    cached = get_cached_data('sector_rotation')
    if cached:
        return jsonify(cached)
    result = sector_analyzer.analyze(period=20)
    set_cached_data('sector_rotation', result)
    return jsonify(result)


@app.route("/api/capital-flow")
def api_capital_flow():
    cached = get_cached_data('capital_flow')
    if cached:
        return jsonify(cached)
    result = flow_analyzer.analyze()
    set_cached_data('capital_flow', result)
    return jsonify(result)


@app.route("/api/sentiment")
def api_sentiment():
    cached = get_cached_data('sentiment')
    if cached:
        return jsonify(cached)
    result = sentiment_analyzer.analyze()
    set_cached_data('sentiment', result)
    return jsonify(result)


@app.route("/api/screen-stocks")
def api_screen_stocks():
    strategy = request.args.get("strategy", "breakout")
    top_n = int(request.args.get("top_n", 20))
    cache_key = f'stocks_{strategy}_{top_n}'
    cached = get_cached_data(cache_key)
    if cached:
        return jsonify(cached)
    selector = StockSelector(lambda: fetcher.fetch_stock_list())
    stocks = selector.screen_by_strategy(strategy, top_n)
    set_cached_data(cache_key, stocks)
    return jsonify(stocks)


@app.route("/api/backtest")
def api_backtest():
    engine = BacktestEngine(config, fetcher)
    result = engine.run("000001", period=500)
    return jsonify({
        "total_return": result.total_return,
        "annual_return": result.annual_return,
        "sharpe_ratio": result.sharpe_ratio,
        "max_drawdown": result.max_drawdown,
        "win_rate": result.win_rate,
        "total_trades": result.total_trades,
        "profit_factor": result.profit_factor,
        "avg_profit": result.avg_profit,
        "avg_loss": result.avg_loss,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
    })


@app.route("/api/quick")
def api_quick():
    market_trend = market_analyzer.analyze("000001", period=120)
    sentiment = sentiment_analyzer.analyze()
    capital_flow = flow_analyzer.analyze()
    signal = signal_generator.generate(
        market_trend, {"rotation_signal": {}, "top_sectors": []},
        capital_flow, sentiment,
    )
    return jsonify({
        "meta": {"analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        "market_trend": market_trend,
        "sentiment": sentiment,
        "capital_flow": capital_flow,
        "trading_signal": {
            "action": signal.action, "strength": signal.strength,
            "score": signal.score, "reasons": signal.reasons,
            "warnings": signal.warnings,
        },
    })


@app.route("/api/health")
def health():
    import psutil
    process = psutil.Process()
    memory_usage = process.memory_info().rss / (1024 * 1024)  # MB
    cpu_percent = process.cpu_percent()
    
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat(),
        "system": {
            "memory_mb": round(memory_usage, 2),
            "cpu_percent": cpu_percent,
            "cache_size": len(_cache),
        },
        "version": "1.0.0",
    })


@app.route("/api/cache-info")
def cache_info():
    info = {}
    with _cache_lock:
        for key, item in _cache.items():
            info[key] = {
                "age_seconds": round(datetime.now().timestamp() - item['timestamp'], 2),
                "size_bytes": len(str(item['data']).encode('utf-8'))
            }
    return jsonify(info)


@app.route("/api/clear-cache")
def clear_cache_endpoint():
    clear_cache()
    return jsonify({"status": "ok", "message": "Cache cleared"})


if __name__ == "__main__":
    try:
        print("Starting A股量化交易系统...")
        print("Running on http://127.0.0.1:5000")
        app.run(host="127.0.0.1", port=5000, debug=False, threaded=True, use_reloader=False)
    except Exception as e:
        print(f"Failed to start server: {e}")
        import traceback
        traceback.print_exc()
