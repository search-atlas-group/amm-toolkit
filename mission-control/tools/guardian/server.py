#!/usr/bin/env python3
"""
AMM Guardian Dashboard
Run: python3 projects/guardian/server.py
Then open: http://localhost:7433
"""
import http.server, socketserver, json, os, sqlite3
from urllib.parse import urlparse, parse_qs

PORT = 7433
HERE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.normpath(os.path.join(HERE, '..', '..', 'amm-guardian', 'guardian.db'))


def query(sql, params=()):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} {fmt % args}')

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')

    def _json(self, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p  = urlparse(self.path)
        qs = parse_qs(p.query)

        if p.path in ('/', '/index.html'):
            self._file(os.path.join(HERE, 'index.html'), 'text/html; charset=utf-8')
        elif p.path == '/api/status':
            self._status()
        elif p.path == '/api/signals':
            source = qs.get('source', [''])[0]
            status = qs.get('status', [''])[0]
            limit  = int(qs.get('limit', ['60'])[0])
            self._signals(source, status, limit)
        elif p.path == '/api/suggestions':
            self._suggestions()
        elif p.path == '/ping':
            self._json({'ok': True})
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

    def _status(self):
        if not os.path.isfile(DB):
            self._json({'error': f'guardian.db not found at {DB}'})
            return

        runs = query(
            "SELECT run_type, started_at, finished_at, signals_processed, suggestions_created "
            "FROM run_log ORDER BY id DESC LIMIT 20"
        )
        last = {}
        for r in runs:
            if r['run_type'] not in last:
                last[r['run_type']] = r

        counts = query(
            "SELECT source, status, COUNT(*) as n FROM signals "
            "GROUP BY source, status ORDER BY source, status"
        )
        by_source = {}
        for row in counts:
            s = row['source']
            if s not in by_source:
                by_source[s] = {'total': 0}
            by_source[s][row['status']] = row['n']
            by_source[s]['total'] += row['n']

        pending_s  = query("SELECT COUNT(*) as n FROM suggestions WHERE status='pending'")[0]['n']
        total_s    = query("SELECT COUNT(*) as n FROM suggestions")[0]['n']
        total_sig  = query("SELECT COUNT(*) as n FROM signals")[0]['n']

        self._json({
            'db_path':           DB,
            'last_runs':         last,
            'signals_by_source': by_source,
            'total_signals':     total_sig,
            'pending_suggestions': pending_s,
            'total_suggestions': total_s,
        })

    def _signals(self, source, status, limit):
        if not os.path.isfile(DB):
            self._json({'signals': [], 'error': 'db not found'})
            return
        where, params = [], []
        if source:
            where.append('source=?')
            params.append(source)
        if status:
            where.append('status=?')
            params.append(status)
        clause = ('WHERE ' + ' AND '.join(where)) if where else ''
        rows = query(
            f"SELECT id, source, signal_key, status, collected_at, analyzed_at "
            f"FROM signals {clause} ORDER BY id DESC LIMIT ?",
            params + [limit]
        )
        self._json({'signals': rows, 'count': len(rows)})

    def _suggestions(self):
        if not os.path.isfile(DB):
            self._json({'suggestions': [], 'error': 'db not found'})
            return
        rows = query(
            "SELECT id, type, confidence, target, title, status, github_url, created_at, executed_at "
            "FROM suggestions ORDER BY id DESC LIMIT 100"
        )
        self._json({'suggestions': rows})


if __name__ == '__main__':
    print(f'\n  AMM Guardian Dashboard')
    print(f'  http://localhost:{PORT}')
    print(f'  DB: {DB}')
    if not os.path.isfile(DB):
        print(f'  WARNING: guardian.db not found — is amm-guardian running?')
    print(f'\n  Ctrl+C to stop\n')
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('localhost', PORT), Handler) as srv:
        srv.serve_forever()
