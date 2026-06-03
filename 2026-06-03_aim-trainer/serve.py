"""Aim Trainer 로컬 수집 서버.
- 정적 파일(index.html) 서빙
- POST /log  : 한 판 기록을 stats.json 에 append
- GET  /stats: 저장된 전체 기록 반환
stats.json 은 같은 폴더에 생성되며, Claude(Sol)가 직접 Read 로 읽어 분석한다.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
STATS = os.path.join(HERE, "stats.json")
PORT = 8731


def load_stats():
    if not os.path.exists(STATS):
        return []
    try:
        with open(STATS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/stats"):
            return self._send(200, json.dumps(load_stats(), ensure_ascii=False).encode("utf-8"))
        if path == "/":
            path = "/index.html"
        fp = os.path.normpath(os.path.join(HERE, path.lstrip("/")))
        if fp.startswith(HERE) and os.path.isfile(fp):
            ctype = "text/html; charset=utf-8" if fp.endswith(".html") else "application/octet-stream"
            with open(fp, "rb") as f:
                return self._send(200, f.read(), ctype)
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if not self.path.startswith("/log"):
            return self._send(404)
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            return self._send(400, b'{"ok":false}')
        recs = load_stats()
        recs.append(rec)
        with open(STATS, "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=2)
        self._send(200, b'{"ok":true}')

    def log_message(self, *args):
        pass  # quiet


if __name__ == "__main__":
    print(f"Aim Trainer server: http://localhost:{PORT}/index.html")
    print(f"기록 파일: {STATS}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
