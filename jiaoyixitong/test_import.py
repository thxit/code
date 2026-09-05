import sys
sys.path.insert(0, 'd:/code/jiaoyixitong')

print("Testing imports for serve.py...")

try:
    from waitress import serve
    print("waitress OK")
except Exception as e:
    print(f"waitress failed: {e}")

try:
    from flask import Flask, render_template, jsonify, request
    print("flask OK")
except Exception as e:
    print(f"flask failed: {e}")

try:
    from flask_cors import CORS
    print("flask_cors OK")
except Exception as e:
    print(f"flask_cors failed: {e}")

try:
    from config.settings import get_config
    print("config.settings OK")
except Exception as e:
    print(f"config.settings failed: {e}")

try:
    from data.fetcher import DataFetcher
    print("data.fetcher OK")
except Exception as e:
    print(f"data.fetcher failed: {e}")

try:
    from analysis.market_trend import MarketTrendAnalyzer
    print("analysis.market_trend OK")
except Exception as e:
    print(f"analysis.market_trend failed: {e}")

print("Import test completed")