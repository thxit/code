import sys
import os
import multiprocessing

def start_server():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from flask import Flask, render_template, jsonify, request
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/health')
    def health():
        return jsonify({"status": "ok"})
    
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    print("Starting server in separate process...")
    process = multiprocessing.Process(target=start_server)
    process.start()
    print("Server process started with PID:", process.pid)
    process.join()