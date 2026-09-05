import sys
import os
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

# 测试步骤：逐步添加模块
step = 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "step": step, "time": datetime.now().isoformat()})

@app.route('/api/step1')
def step1():
    global step
    step = 1
    print("Step 1: Loading config...")
    from config.settings import get_config
    config = get_config()
    return jsonify({"status": "ok", "step": 1, "message": "Config loaded"})

@app.route('/api/step2')
def step2():
    global step
    step = 2
    print("Step 2: Creating DataFetcher...")
    from config.settings import get_config
    from data.fetcher import DataFetcher
    config = get_config()
    fetcher = DataFetcher(config)
    return jsonify({"status": "ok", "step": 2, "message": "DataFetcher created"})

@app.route('/api/step3')
def step3():
    global step
    step = 3
    print("Step 3: Creating MarketTrendAnalyzer...")
    from config.settings import get_config
    from data.fetcher import DataFetcher
    from analysis.market_trend import MarketTrendAnalyzer
    config = get_config()
    fetcher = DataFetcher(config)
    analyzer = MarketTrendAnalyzer(config, fetcher)
    return jsonify({"status": "ok", "step": 3, "message": "MarketTrendAnalyzer created"})

@app.route('/api/step4')
def step4():
    global step
    step = 4
    print("Step 4: Running analysis...")
    from config.settings import get_config
    from data.fetcher import DataFetcher
    from analysis.market_trend import MarketTrendAnalyzer
    config = get_config()
    fetcher = DataFetcher(config)
    analyzer = MarketTrendAnalyzer(config, fetcher)
    result = analyzer.analyze("000001", period=100)
    return jsonify({"status": "ok", "step": 4, "result": result.get("summary", "No summary")})

if __name__ == "__main__":
    print("Starting debug server...")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)