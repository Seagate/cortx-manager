function log(text) {
    let li = document.createElement('li');
    li.innerHTML = text;
    document.getElementById('log').appendChild(li);
}

// log('window.location         : ' + window.location);
// log('window.location.hash    : ' + window.location.hash);
// log('window.location.host    : ' + window.location.host);
// log('window.location.hostname: ' + window.location.hostname);
// log('window.location.href    : ' + window.location.href);
// log('window.location.origin  : ' + window.location.origin);
// log('window.location.pathname: ' + window.location.pathname);
// log('window.location.port    : ' + window.location.port);
// log('window.location.protocol: ' + window.location.protocol);
// log('window.location.search  : ' + window.location.search);
// log('hostname defined? ' + ('hostname' in window.location))

function mkuri(protocol, host, port, path = '') {
    return protocol + '://'
        + (host ? host : 'localhost') + ':'
        + port + '/'
        + path
        ;
}

// const wsport = 8081
// const wsport = 8080
// const wsport = 7681
// const wsport = 9100
//const wsport = 8765;
//const wsuri = mkuri('ws', window.location.hostname, wsport);
const wsport = window.location.port;
//const wsuri = mkuri('ws', window.location.hostname, wsport, 'ws');
const wsuri = mkuri('ws', window.location.hostname, wsport, 'ws');

log('websocket: ' + wsuri);

var socket = new WebSocket(wsuri);

socket.onopen = function (event) {
    log('SOCK-OPEN: Opened connection 🎉');
    send('HELLO');
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

    let msg = document.getElementById('message').value;
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
