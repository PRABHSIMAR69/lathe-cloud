import time
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-lathe-cloud-secure'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# The cloud data vault starts empty with a last_seen of 0
stored_snapshot = {
    "latest": {
        "temp": 0.0, "current": 0.0, "voltage": 0.0, "thd": 0.0, "rpm": 0.0,
        "motor_on": False, "alerts": [],
        "oee": {"oee": 0.0, "availability": 0.0, "performance": 0.0, "quality": 0.0}
    },
    "history": {"temp": [], "current": [], "voltage": [], "thd": [], "rpm": [], "time": []},
    "last_seen": 0.0
}

@app.route('/api/push', methods=['POST'])
def receive_data():
    """Catches the complete snapshot payload streamed from the Raspberry Pi."""
    global stored_snapshot
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid data payload"}), 400
    
    # Store data and timestamp it with the cloud clock
    stored_snapshot["latest"] = payload.get("latest", stored_snapshot["latest"])
    stored_snapshot["history"] = payload.get("history", stored_snapshot["history"])
    stored_snapshot["last_seen"] = time.time()
    
# Mirror everything directly to all open browsers
    socketio.emit('update', stored_snapshot)
    return jsonify({"status": "synced", "cloud_time": stored_snapshot["last_seen"]})

@app.route('/api/latest', methods=['GET'])
def get_latest():
    snap = dict(stored_snapshot)
    snap['server_age_ms'] = int((time.time() - stored_snapshot['last_seen']) * 1000)
    return jsonify(snap)

@app.route('/')

@app.route('/')
def index():
    return render_template_string(PAGE)

# --- FULL SCALE INDUSTRIAL CONTROL PANEL FRONTEND ---
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Lathe Cloud Monitor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
<style>
:root{
  --bg:#f0f4f8; --surface:#ffffff; --surface-2:#f7fafc;
  --header:#1a3353; --header-fg:#ffffff;
  --primary:#2b6cb0; --primary-hover:#2c5282;
  --success:#276749; --warning:#744210; --danger:#9b2c2c;
  --warning-bg:#fefcbf; --danger-bg:#fed7d7; --success-bg:#c6f6d5;
  --text:#1a202c; --text-muted:#4a5568; --text-soft:#718096;
  --border:#e2e8f0; --border-strong:#cbd5e0;
  --shadow:0 1px 3px rgba(0,0,0,0.10), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-sm:0 1px 2px rgba(0,0,0,0.06);
  --radius:8px;
  --c-temp:#c53030; --c-rpm:#2b6cb0; --c-current:#b7791f;
  --c-voltage:#6b46c1; --c-thd:#c05621; --c-motor:#276749;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:'DM Sans',system-ui,-apple-system,sans-serif;font-size:14px;line-height:1.5;}
.num{font-family:'Fira Code',monospace;font-variant-numeric:tabular-nums;}
.app{min-height:100vh;display:flex;flex-direction:column;position:relative;}
.header{background:var(--header);color:var(--header-fg);padding:14px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px;position:sticky;top:0;z-index:30;box-shadow:var(--shadow);}
.brand{display:flex;align-items:center;gap:12px;}
.brand-mark{width:32px;height:32px;background:var(--primary);border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;}
.brand-title{font-size:16px;font-weight:600;letter-spacing:.2px;}
.brand-sub{font-size:11px;opacity:.75;text-transform:uppercase;letter-spacing:1px;}
.status-pill{display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);padding:6px 12px;border-radius:999px;font-size:12px;}
.status-dot{width:8px;height:8px;border-radius:50%;background:#9ae6b4;}
.status-dot.off{background:#fc8181;}
.tabs{background:var(--surface);border-bottom:1px solid var(--border);padding:0 16px;display:flex;gap:2px;position:sticky;top:60px;z-index:25;overflow-x:auto;}
.tab{padding:12px 18px;border:none;background:transparent;cursor:pointer;font-family:inherit;font-size:13px;font-weight:500;color:var(--text-muted);border-bottom:3px solid transparent;transition:all .15s;}
.tab.active{color:var(--primary);border-bottom-color:var(--primary);font-weight:600;}
main{flex:1;padding:20px;max-width:1400px;margin:0 auto;width:100%;}
.page{display:none;} .page.active{display:block;}
.section-title{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--text-soft);margin:0 0 10px 4px;}
.metrics{display:grid;gap:12px;margin-bottom:18px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));}
.metric{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--primary);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow-sm);position:relative;}
.metric--temp{border-left-color:var(--c-temp);} .metric--rpm{border-left-color:var(--c-rpm);} .metric--current{border-left-color:var(--c-current);} .metric--voltage{border-left-color:var(--c-voltage);} .metric--thd{border-left-color:var(--c-thd);} .metric--motor{border-left-color:var(--c-motor);}
.metric-label{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--text-soft);font-weight:600;margin-bottom:6px;}
.metric-value{font-family:'Fira Code',monospace;font-size:26px;font-weight:500;color:var(--text);line-height:1.1;display:flex;align-items:baseline;gap:4px;}
.metric-unit{font-size:13px;color:var(--text-muted);font-weight:400;}
.progress{margin-top:10px;height:5px;background:var(--surface-2);border-radius:3px;overflow:hidden;}
.progress-fill{height:100%;background:var(--primary);transition:width .3s ease;}
.metric--temp .progress-fill{background:var(--c-temp);} .metric--rpm .progress-fill{background:var(--c-rpm);} .metric--current .progress-fill{background:var(--c-current);} .metric--voltage .progress-fill{background:var(--c-voltage);} .metric--thd .progress-fill{background:var(--c-thd);}
.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;text-transform:uppercase;}
.badge--on{background:var(--success-bg);color:var(--success);} .badge--off{background:#edf2f7;color:var(--text-muted);}
.row-2{display:grid;gap:16px;grid-template-columns:1fr 1fr;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow-sm);padding:18px;}
.card h3{margin:0 0 12px;font-size:14px;font-weight:600;}
.oee-grid{display:grid;gap:10px;grid-template-columns:repeat(4,1fr);}
.oee-cell{padding:14px 12px;background:var(--surface-2);border-radius:6px;border:1px solid var(--border);text-align:center;}
.oee-cell-label{font-size:10px;text-transform:uppercase;color:var(--text-soft);font-weight:600;}
.oee-cell-val{font-family:'Fira Code',monospace;font-size:22px;font-weight:500;margin-top:4px;}
.oee-cell--main{background:#ebf5ff;border-color:#bee3f8;} .oee-cell--main .oee-cell-val{color:var(--primary);}
.charts-grid{display:grid;gap:16px;grid-template-columns:1fr 1fr;}
.chart-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow-sm);height:280px;display:flex;flex-direction:column;}
.chart-card h4{margin:0 0 8px;font-size:13px;font-weight:600;color:var(--text-muted);text-transform:uppercase;}
.chart-wrap{flex:1;position:relative;}
.alert-banner{background:var(--danger-bg);color:var(--danger);border-left:4px solid var(--danger);padding:12px 16px;border-radius:var(--radius);margin-bottom:16px;font-weight:500;display:none;align-items:center;gap:10px;}
.alert-banner.on{display:flex;}

/* OFFLINE FULL-SCREEN GLASS OVERLAY */
.offline-overlay {
    position: fixed; inset: 0; background: rgba(240, 244, 248, 0.85);
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    z-index: 9999; display: flex; flex-direction: column;
    align-items: center; justify-content: center; transition: opacity 0.4s ease;
}
.offline-overlay.hidden { opacity: 0; pointer-events: none; }
.offline-box {
    background: white; padding: 40px; border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.1); border-top: 4px solid var(--danger); text-align: center;
}
.offline-title { font-size: 24px; font-weight: 700; color: var(--danger); margin-bottom: 8px; }
.offline-text { color: var(--text-muted); font-size: 14px; max-width: 320px; }
</style>
</head>
<body>



<div class="app">
    <header class="header">
      <div class="brand">
        <div class="brand-mark">SL</div>
        <div>
          <div class="brand-title">Smart Lathe Monitor</div>
          <div class="brand-sub">Cloud Control Hub</div>
        </div>
      </div>
      <div class="status-pill"><span class="status-dot" id="connDot"></span><span id="connTxt">Cloud Connected</span></div>
    </header>
    
    <nav class="tabs" id="tabs">
      <button class="tab active" data-tab="dashboard">Dashboard</button>
      <button class="tab" data-tab="trends">Trends</button>
    </nav>
    
    <main>
      <div class="alert-banner" id="alertBanner">
        <span id="alertText">Active critical alerts</span>
      </div>
      
      <section class="page active" id="page-dashboard">
        <div class="section-title">Live Remote Readings</div>
        <div class="metrics">
          <div class="metric metric--temp">
            <div class="metric-label">Temperature</div>
            <div class="metric-value"><span class="num" id="tempVal">--</span><span class="metric-unit">°C</span></div>
            <div class="progress"><div class="progress-fill" id="tempBar" style="width:0%"></div></div>
          </div>
          <div class="metric metric--rpm">
            <div class="metric-label">Spindle RPM</div>
            <div class="metric-value"><span class="num" id="rpmVal">--</span></div>
            <div class="progress"><div class="progress-fill" id="rpmBar" style="width:0%"></div></div>
          </div>
          <div class="metric metric--current">
            <div class="metric-label">Current Draw</div>
            <div class="metric-value"><span class="num" id="curVal">--</span><span class="metric-unit">A</span></div>
            <div class="progress"><div class="progress-fill" id="curBar" style="width:0%"></div></div>
          </div>
          <div class="metric metric--voltage">
            <div class="metric-label">Line Voltage</div>
            <div class="metric-value"><span class="num" id="voltVal">--</span><span class="metric-unit">V</span></div>
            <div class="progress"><div class="progress-fill" id="voltBar" style="width:0%"></div></div>
          </div>
          <div class="metric metric--thd">
            <div class="metric-label">Total Harmonic Distortion</div>
            <div class="metric-value"><span class="num" id="thdVal">--</span><span class="metric-unit">%</span></div>
            <div class="progress"><div class="progress-fill" id="thdBar" style="width:0%"></div></div>
          </div>
          <div class="metric metric--motor">
            <div class="metric-label">Motor Status</div>
            <div class="metric-value" style="margin-top:6px;"><span class="badge badge--off" id="motorBadge">OFFLINE</span></div>
          </div>
        </div>
        
        <div class="row-2">
          <div class="card">
            <h3>Calculated Shift OEE</h3>
            <div class="oee-grid">
              <div class="oee-cell oee-cell--main"><div class="oee-cell-label">OEE</div><div class="oee-cell-val num" id="oeeMain">--</div></div>
              <div class="oee-cell"><div class="oee-cell-label">Availability</div><div class="oee-cell-val num" id="oeeAvail">--</div></div>
              <div class="oee-cell"><div class="oee-cell-label">Performance</div><div class="oee-cell-val num" id="oeePerf">--</div></div>
              <div class="oee-cell"><div class="oee-cell-label">Quality</div><div class="oee-cell-val num" id="oeeQual">--</div></div>
            </div>
          </div>
        </div>
      </section>
      
      <section class="page" id="page-trends">
        <div class="section-title">Historical Telemetry Window</div>
        <div class="charts-grid">
          <div class="chart-card"><h4>Temperature History (°C)</h4><div class="chart-wrap"><canvas id="chTemp"></canvas></div></div>
          <div class="chart-card"><h4>Speed Trend (RPM)</h4><div class="chart-wrap"><canvas id="chRpm"></canvas></div></div>
          <div class="chart-card"><h4>Current Loading (A)</h4><div class="chart-wrap"><canvas id="chCur"></canvas></div></div>
          <div class="chart-card"><h4>Power THD Profile (%)</h4><div class="chart-wrap"><canvas id="chThd"></canvas></div></div>
        </div>
      </section>
    </main>
</div>

<script>
'use strict';
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// Tab switching mechanism
$$('.tab').forEach(b => b.addEventListener('click', () => {
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.page').forEach(p => p.classList.remove('active'));
    b.classList.add('active');
    $(`#page-${b.dataset.tab}`).classList.add('active');
    if(b.dataset.tab === 'trends') { ensureCharts(); }
}));

let __charts = null;
const sock = io();

sock.on('connect', () => { 
    $('#connDot').style.background = "#9ae6b4"; 
    $('#connTxt').textContent = "Cloud Active"; 
});

sock.on('disconnect', () => { 
    $('#connDot').style.background = "#fc8181"; 
    $('#connTxt').textContent = "Reconnecting..."; 
});

let _lastUpdate = 0;

async function fetchLatest() {
    try {
        const res = await fetch('/api/latest?t=' + Date.now());
        const snap = await res.json();
        const serverAge = snap.server_age_ms || 0;
        if (serverAge > 15000) {
            _lastUpdate = 0;
        } else {
            _lastUpdate = Date.now();
        }
        $('#connDot').style.background = '#9ae6b4';
        $('#connTxt').textContent = 'Cloud Active';
        renderLatest(snap.latest);
        if (__charts && snap.history) { applyHistory(snap.history); }
    } catch(e) {
        $('#connDot').style.background = '#fc8181';
        $('#connTxt').textContent = 'Reconnecting...';
    }
}

fetchLatest();
setInterval(fetchLatest, 2000);

setInterval(() => {
    if (_lastUpdate > 0 && (Date.now() - _lastUpdate > 15000)) {
        $('#connDot').style.background = '#fc8181';
        $('#connTxt').textContent = 'Machine Offline';
        const mb = $('#motorBadge');
        mb.textContent = 'MACHINE OFF';
        mb.className = 'badge badge--off';
    }
}, 3000);

const fmt = (v, d=1) => (v == null || isNaN(v)) ? '--' : Number(v).toFixed(d);

function renderLatest(L) {
    $('#tempVal').textContent = fmt(L.temp, 1);
    if (L.motor_on && L.rpm > 0) window._lastRpm = L.rpm;
    $('#rpmVal').textContent  = L.motor_on ? fmt(window._lastRpm || L.rpm, 0) : '0';
    $('#curVal').textContent  = fmt(L.current, 2);
    $('#voltVal').textContent = fmt(L.voltage, 1);
    $('#thdVal').textContent  = fmt(L.thd, 2);
    
    $('#tempBar').style.width = Math.min(100, (L.temp / 80)*100) + '%';
    $('#rpmBar').style.width = Math.min(100, ((window._lastRpm || L.rpm) / 1200)*100) + '%';
    $('#curBar').style.width = Math.min(100, (L.current / 5)*100) + '%';
    $('#voltBar').style.width = Math.min(100, (L.voltage / 260)*100) + '%';
    $('#thdBar').style.width = Math.min(100, (L.thd / 15)*100) + '%';
    
    const mb = $('#motorBadge');
    mb.textContent = L.motor_on ? 'RUNNING' : 'IDLE';
    mb.className = 'badge ' + (L.motor_on ? 'badge--on' : 'badge--off');
    
    if(L.alerts && L.alerts.length) {
        $('#alertBanner').classList.add('on');
        $('#alertText').textContent = "CRITICAL WARNINGS: " + L.alerts.join(', ');
    } else {
        $('#alertBanner').classList.remove('on');
    }
    
    const O = L.oee || {};
    $('#oeeMain').textContent = fmt(O.oee, 1) + '%';
    $('#oeeAvail').textContent = fmt(O.availability, 1) + '%';
    $('#oeePerf').textContent = fmt(O.performance, 1) + '%';
    $('#oeeQual').textContent = fmt(O.quality, 1) + '%';
}

function ensureCharts() {
    if (__charts) return;
    const baseOpts = {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: { x: { display: false }, y: { grid: { color: '#edf2f7' } } },
        elements: { point: { radius: 0 }, line: { tension: 0.3, borderWidth: 2 } }
    };
    const make = (id, color) => new Chart(document.getElementById(id), {
        type: 'line', data: { labels: Array(60).fill(''), datasets: [{ data: [], borderColor: color, backgroundColor: color+'11', fill: true }] }, options: baseOpts
    });
    __charts = {
        temp: make('chTemp', '#c53030'), rpm: make('chRpm', '#2b6cb0'), cur: make('chCur', '#b7791f'), thd: make('chThd', '#c05621')
    };
}

function applyHistory(H) {
    const set = (c, arr) => { if(arr) { c.data.datasets[0].data = arr; c.update('none'); } };
    set(__charts.temp, H.temp); set(__charts.rpm, H.rpm); set(__charts.cur, H.current); set(__charts.thd, H.thd);
}
</script>
</body>
</html>
"""

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
