"""DeepSeek Personal Assistant — local proxy + usage tracker.

Serves a chat interface and automatically records token usage for
all API calls. Usage data persists in usage_tracker.json.
"""

import http.server
import json
import os
import datetime
import threading
import ssl
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API_KEY = "sk-1b8beb6163264a649e21cbf2f19d7d64"
DEEPSEEK = "https://api.deepseek.com"
PORT = 8871
TRACKER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage_tracker.json")
_lock = threading.Lock()

ctx = ssl.create_default_context()
try:
    import certifi
    ctx.load_verify_locations(certifi.where())
except Exception:
    pass


def _read_tracker():
    try:
        with open(TRACKER_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_tracker(data):
    with _lock:
        with open(TRACKER_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def _get_rates(model):
    """Return (prompt_rate_per_1k, completion_rate_per_1k) for a model."""
    if "pro" in model:
        return 0.002, 0.008
    return 0.00015, 0.0006

def _get_all_models(tracker):
    """Collect model names and totals across all days."""
    names = set()
    totals = {}
    for day_data in tracker.values():
        for k, v in day_data.items():
            if k == "_total": continue
            if isinstance(v, dict) and "requests" in v:
                names.add(k)
                if k not in totals:
                    totals[k] = {"total_tokens": 0, "requests": 0, "cost": 0.0}
                totals[k]["total_tokens"] += v.get("total_tokens", 0)
                totals[k]["requests"] += v.get("requests", 0)
                totals[k]["cost"] += v.get("cost", 0)
    return {"names": sorted(names), "totals": {k: {kk: round(vv, 6) if kk == "cost" else vv for kk, vv in v.items()} for k, v in totals.items()}}


def _record_usage(response_data):
    usage = response_data.get("usage", {}) if response_data else {}
    if not usage:
        return
    today = datetime.date.today().isoformat()
    model = response_data.get("model", "unknown")
    tracker = _read_tracker()
    day = tracker.setdefault(today, {})
    # Per-model
    m = day.setdefault(model, {
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
        "requests": 0, "cost": 0.0
    })
    m["prompt_tokens"] += usage.get("prompt_tokens", 0)
    m["completion_tokens"] += usage.get("completion_tokens", 0)
    m["total_tokens"] += usage.get("total_tokens", 0)
    m["requests"] += 1
    pr, cr = _get_rates(model)
    m["cost"] += usage.get("prompt_tokens", 0) / 1000 * pr + usage.get("completion_tokens", 0) / 1000 * cr
    # Total across models
    total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "requests": 0, "cost": 0.0}
    for k, v in day.items():
        if isinstance(v, dict) and "requests" in v:
            for key in total:
                total[key] += v.get(key, 0)
    day["_total"] = total
    _write_tracker(tracker)


def _fetch_deepseek(method, path, body=None, stream=False):
    """Forward request to DeepSeek and return (status, headers, body_bytes)."""
    url = f"{DEEPSEEK}{path}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        resp = urlopen(req, context=ctx, timeout=60)
        return resp.status, dict(resp.headers), resp.read()
    except HTTPError as e:
        return e.code, dict(e.headers), e.read()


class Handler(http.server.SimpleHTTPRequestHandler):
    def _send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/balance":
            status, headers, body = _fetch_deepseek("GET", "/user/balance")
            try:
                data = json.loads(body) if body else {}
            except Exception:
                data = {"raw": body.decode(errors="replace")}
            self._send_json(status, data)
            return
        if self.path == "/api/usage":
            tracker = _read_tracker()
            self._send_json(200, {
                "days": tracker,
                "today": tracker.get(datetime.date.today().isoformat(), {}),
                "total_requests": sum(d.get("requests", 0) for d in tracker.values()),
                "total_tokens": sum(d.get("total_tokens", 0) for d in tracker.values()),
                "total_cost": round(sum(d.get("cost", 0) for d in tracker.values()), 6),
            })
            return
        # Serve static files
        if self.path in ("", "/"):
            self.path = "/index.html"
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path in ("/v1/chat/completions", "/api/chat"):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                req_body = json.loads(raw)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
                return

            # Forward to DeepSeek
            status, resp_headers, resp_body = _fetch_deepseek(
                "POST", "/chat/completions", body=req_body
            )
            try:
                resp_data = json.loads(resp_body) if resp_body else {}
            except Exception:
                resp_data = {"raw": resp_body.decode(errors="replace")}

            # Record usage
            _record_usage(resp_data)

            # Return response
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_body)
            return

        self._send_json(404, {"error": "Not found"})


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"DeepSeek Personal Assistant running at http://127.0.0.1:{PORT}")
    print(f"Tracker file: {TRACKER_FILE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
