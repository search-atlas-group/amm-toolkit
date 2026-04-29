#!/usr/bin/env python3
"""
Tier 2 Hub — serves the ClientOps and T2 Triage tools
Run: python3 'projects/Tier 2/server.py'
Then open: http://localhost:7434

Requires the individual backends to be running:
  ClientOps Backend:    cd 'Work stuff/clientops-backend' && python main.py   (port 8000)
  Intercom T2 Triage:   cd 'Work stuff/intercom-t2-triage' && python main.py  (port 8001)
"""
import http.server, socketserver, json, os, urllib.request, urllib.error
from urllib.parse import urlparse

PORT = 7434
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))

TOOLS = {
    'clientops': {
        'label':    'ClientOps Backend',
        'html':     os.path.join(ROOT, 'Work stuff', 'clientops-backend', 'clientops.html'),
        'api_port': 8000,
        'path':     '/clientops',
    },
    't2-triage': {
        'label':    'Intercom T2 Triage',
        'html':     os.path.join(ROOT, 'Work stuff', 'intercom-t2-triage', 'triage-panel.html'),
        'api_port': 8001,
        'path':     '/t2-triage',
    },
}


def backend_alive(port):
    try:
        urllib.request.urlopen(f'http://localhost:{port}/health', timeout=1)
        return True
    except Exception:
        return False


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} {fmt % args}')

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')

    def _html(self, body, status=200):
        data = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self._html('<h1>404 — file not found</h1>', 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)

        if p.path in ('/', '/index.html'):
            self._file(os.path.join(HERE, 'index.html'))
        elif p.path == '/clientops':
            self._file(TOOLS['clientops']['html'])
        elif p.path == '/t2-triage':
            self._file(TOOLS['t2-triage']['html'])
        elif p.path == '/api/health':
            self._json({
                'clientops':  backend_alive(8000),
                't2_triage':  backend_alive(8001),
            })
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    print(f'\n  Tier 2 Hub')
    print(f'  http://localhost:{PORT}')
    for key, t in TOOLS.items():
        exists = os.path.isfile(t['html'])
        print(f'  {"✓" if exists else "✗"} {t["label"]} → localhost:{PORT}{t["path"]}')
    print(f'\n  Ctrl+C to stop\n')
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('localhost', PORT), Handler) as srv:
        srv.serve_forever()
