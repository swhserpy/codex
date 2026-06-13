"""DeepSeek Usage Dashboard — local proxy server.

Serves the dashboard frontend and proxies requests to api.deepseek.com
so the browser can avoid CORS issues. Reads DEEPSEEK_API_KEY from the
environment, or the frontend can supply one via ?key= in query params.
"""

import http.server
import json
import os
import urllib.parse
import urllib.request

PORT = 8877
DEEPSEEK_BASE = "https://api.deepseek.com"


def fetch_deepseek(path, api_key):
    """Forward a GET request to the DeepSeek API and return (status, body)."""
    url = f"{DEEPSEEK_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 500, str(e)


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def _send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _api_key(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        key = qs.get("key", [None])[0]
        return key or os.environ.get("DEEPSEEK_API_KEY", "")

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/balance":
            api_key = self._api_key()
            if not api_key:
                self._send_json(400, {"error": "Missing API key"})
                return
            status, body = fetch_deepseek("/user/balance", api_key)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body}
            self._send_json(status, data)
            return

        if parsed.path == "/api/usage":
            api_key = self._api_key()
            if not api_key:
                self._send_json(400, {"error": "Missing API key"})
                return
            qs = urllib.parse.parse_qs(parsed.query)
            start = qs.get("start", [None])[0]
            end = qs.get("end", [None])[0]
            path = "/billing/usage"
            params = []
            if start:
                params.append(f"start_date={start}")
            if end:
                params.append(f"end_date={end}")
            if params:
                path += "?" + "&".join(params)
            status, body = fetch_deepseek(path, api_key)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body}
            self._send_json(status, data)
            return

        if parsed.path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    print(f"DeepSeek Dashboard running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
