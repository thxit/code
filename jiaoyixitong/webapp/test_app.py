from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "message": "Test server running"})

@app.route('/api/test')
def test():
    return jsonify({"data": "test"})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=False)