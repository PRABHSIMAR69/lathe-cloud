import time
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lathe-cloud-secure-key'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# In-memory storage for the latest packet sent by the Pi
latest_data = {
    "temp": 0.0, "rpm": 0.0, "current": 0.0, "voltage": 0.0, "thd": 0.0,
    "motor_on": False, "alerts": [],
    "oee": {"oee": 0.0, "availability": 0.0, "performance": 0.0, "quality": 0.0},
    "last_seen": 0.0  # Epoch timestamp
}

# We put the HTML template UP HERE so Python reads it before starting the server
PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Cloud Lathe Monitor</title>
    <script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
    <style>
        body { font-family: sans-serif; background: #f0f4f8; color: #1a202c; text-align: center; padding: 50px; }
        .card { background: white; max-width: 500px; margin: 0 auto; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .status { font-weight: bold; font-size: 24px; padding: 10px; border-radius: 4px; display: inline-block; margin-bottom: 20px; }
        .online { background: #c6f6d5; color: #276749; }
        .offline { background: #fed7d7; color: #9b2c2c; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 20px; font-family: monospace; font-size: 18px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Smart Lathe Cloud Monitor</h2>
        <div id="statusBadge" class="status offline">MACHINE OFFLINE</div>
        
        <div class="grid">
            <div>Temperature: <span id="temp">--</span>°C</div>
            <div>RPM: <span id="rpm">--</span></div>
            <div>Current: <span id="current">--</span>A</div>
            <div>Voltage: <span id="voltage">--</span>V</div>
        </div>
    </div>

    <script>
        const socket = io();
        
        socket.on('cloud_update', (data) => {
            const now = Math.floor(Date.now() / 1000);
            if (now - data.last_seen > 5) {
                document.getElementById('statusBadge').className = "status offline";
                document.getElementById('statusBadge').innerText = "MACHINE OFFLINE";
            } else {
                document.getElementById('statusBadge').className = "status online";
                document.getElementById('statusBadge').innerText = "MACHINE RUNNING";
                document.getElementById('temp').innerText = data.temp;
                document.getElementById('rpm').innerText = data.rpm;
                document.getElementById('current').innerText = data.current;
                document.getElementById('voltage').innerText = data.voltage;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/api/push', methods=['POST'])
def receive_data():
    """Endpoint for the Raspberry Pi to post live sensor payloads."""
    global latest_data
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    latest_data.update(payload)
    latest_data["last_seen"] = time.time()
    
    socketio.emit('cloud_update', latest_data)
    return jsonify({"status": "delivered", "timestamp": latest_data["last_seen"]})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Helper endpoint to check current variables via standard HTTP request."""
    return jsonify(latest_data)

@app.route('/')
def index():
    return render_template_string(PAGE_TEMPLATE)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
