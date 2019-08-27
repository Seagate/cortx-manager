//
// This page is for debugging purposes only. To be deleted later
// when we have tests for aiohttp web sockets.
//

function log(text) {
    var li = document.createElement('li');
    li.innerHTML = text;
    document.getElementById('log').appendChild(li);
}

var api_host = location.hostname || 'localhost';
var api_port = location.port || 8082;
log('WS HOST: ' + api_host);
log('WS PORT: ' + api_port);

var wsurl = 'ws://' + api_host + ':' + api_port + '/ws';
log('WS URL: ' + wsurl);

var socket = new WebSocket(wsurl);
log('Do work');

socket.onopen = function (event) {
    log('SOCK-OPEN: Connection opened');
}

socket.onerror = function (event) {
    log('SOCK-ERR: ' + JSON.stringify(event));
}

socket.onmessage = function (event) {
    log('MSG-RECV: ' + event.data);
}

socket.onclose = function (event) {
    log('SOCK-CLOSE: Connection closed');
}

function send(msg) {
    log('MSG-SEND: ' + msg);
    socket.send(msg);
}

document.getElementById('close').addEventListener('click', function (event) {
    log('CLICK: Closing connection');
    socket.close();
});

document.getElementById('send').addEventListener('click', function (event) {

    var msg = document.getElementById('message').value;
    log('CLICK: Sending message');
    send(msg);
});

window.addEventListener('beforeunload', function () {
    socket.close();
});
