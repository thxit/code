import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from waitress import serve
    from flask import Flask, render_template, jsonify, request
    from flask_cors import CORS

    app = Flask(__name__)
    CORS(app)

    @app.route('/')
    def index():
        return 'Hello from Flask!'

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    print('Server starting on port 5000...')
    serve(app, host='0.0.0.0', port=5000, threads=4)
    
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)