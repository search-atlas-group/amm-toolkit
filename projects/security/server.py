#!/usr/bin/env python3
"""
Security Scan Local Server
Run: python3 projects/security/server.py
Then open: http://localhost:7432
"""
import http.server, socketserver, subprocess, json, os, re
from urllib.parse import urlparse, parse_qs

PORT = 7432
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.normpath(os.path.join(HERE, '..', '..', 'Scripts', 'repo-security-scan.sh'))


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} {fmt % args}')

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)

        if p.path in ('/', '/index.html'):
            self._file(os.path.join(HERE, 'index.html'), 'text/html; charset=utf-8')

        elif p.path == '/ping':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        elif p.path == '/config':
            root = os.path.normpath(os.path.join(HERE, '..', '..'))
            payload = json.dumps({'root': root, 'name': os.path.basename(root)}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self._cors()
            self.end_headers()
            self.wfile.write(payload)

        elif p.path == '/scan':
            url = parse_qs(p.query).get('url', [''])[0].strip()
            if not url:
                self.send_response(400)
                self.end_headers()
                return
            self._scan(url)

        else:
            self.send_response(404)
            self.end_headers()

    def _file(self, path, ctype):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _scan(self, url):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Accel-Buffering', 'no')
        self._cors()
        self.end_headers()

        def push(payload):
            try:
                self.wfile.write(f'data: {json.dumps(payload)}\n\n'.encode())
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        if not os.path.isfile(SCRIPT):
            push({'line': f'Script not found: {SCRIPT}', 'type': 'err'})
            push({'done': True, 'exit_code': 1})
            return

        try:
            proc = subprocess.Popen(
                ['bash', SCRIPT, url],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                if not push({'line': line.rstrip(), 'type': 'out'}):
                    proc.kill()
                    return
            proc.wait()

            report_path = '/tmp/security-scan-results/security-report.json'
            report = None
            if os.path.isfile(report_path):
                with open(report_path) as f:
                    try:
                        report = json.load(f)
                    except Exception:
                        pass

            push({'done': True, 'exit_code': proc.returncode, 'report': report})
        except Exception as e:
            push({'line': f'Server error: {e}', 'type': 'err'})
            push({'done': True, 'exit_code': 1})


if __name__ == '__main__':
    print(f'\n  Repo Security Scanner')
    print(f'  http://localhost:{PORT}')
    print(f'  Script: {SCRIPT}')
    if not os.path.isfile(SCRIPT):
        print(f'  WARNING: script not found — full scans will not run')
    print(f'\n  Ctrl+C to stop\n')
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('localhost', PORT), Handler) as srv:
        srv.serve_forever()
