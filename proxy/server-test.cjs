// server-test.cjs
const http = require('http');
http.createServer((req, res) => {
  res.end('ok');
}).listen(7070, () => console.log('listening on http://localhost:7070'));
