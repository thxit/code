import sys
import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

@app.route('/api/test')
def test():
    return jsonify({"data": "test"})

if __name__ == "__main__":
    print("Starting simple server...")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)