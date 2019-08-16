function log(text) {
    var li = document.createElement('li');
    li.innerHTML = text;
    document.getElementById('log').appendChild(li);
}

// REST API sample:
// http://qb21n1-m05-vm7.mero.colo.seagate.com:8082/csm?cmd=email&action=config&args=xxx

//var socket = new WebSocket('ws://localhost:8081/');
//var socket = new WebSocket('ws://localhost:8080/');
//var socket = new WebSocket('ws://localhost:7681/');

// var wsurl = 'http://qb21n1-m05-vm7.mero.colo.seagate.com:8082/ws';

log('Hello');
var api_host = 'qb21n1-m05-vm7.mero.colo.seagate.com';
log('WS HOST: ' + api_host);
var api_port = 8082;
log('WS PORT: ' + api_port);
var wsurl = 'ws://' + api_host + ':' + api_port + '/ws';
log('WS URL: ' + wsurl);

var socket = new WebSocket(wsurl);
log('Do work');

socket.onopen = function (event) {
    log('SOCK-OPEN: Opened connection 🎉');
    // send('HELLO');
}

socket.onerror = function (event) {
    log('SOCK-ERR: ' + JSON.stringify(event));
}

socket.onmessage = function (event) {
    log('MSG-RECV: ' + event.data);
}

socket.onclose = function (event) {
    log('SOCK-CLOSE: Connection closed! 😱');
}

document.getElementById('close').addEventListener('click', function (event) {
    log('CLICK: Closing connection 😱');
    socket.close();
});

document.getElementById('send').addEventListener('click', function (event) {

    var msg = document.getElementById('message').value;
    log('CLICK: Sending message');
    send(msg);
});

function send(msg) {
    log('MSG-SEND: ' + msg);
    socket.send(msg);
}

window.addEventListener('beforeunload', function () {
    socket.close();
});
