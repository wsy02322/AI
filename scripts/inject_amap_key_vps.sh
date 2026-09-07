#!/usr/bin/env bash
# ST-16: inject Amap Web Service key into OWUI Tool Valves from the VPS.
# Does not print the key. Does not touch WEBUI_SECRET_KEY or openai.api_configs.
# Does not restart the container.
#
# Usage on VPS (as root is fine):
#   export OPENWEBUI_USERNAME='your-admin-login'
#   export OPENWEBUI_PASSWORD='...'
#   read -s AMAP_KEY; echo; export AMAP_KEY
#   bash inject_amap_key_vps.sh
set -euo pipefail

OPENWEBUI_URL="${OPENWEBUI_URL:-http://127.0.0.1:8080}"
OPENWEBUI_URL="${OPENWEBUI_URL%/}"
: "${OPENWEBUI_USERNAME:?set OPENWEBUI_USERNAME}"
: "${OPENWEBUI_PASSWORD:?set OPENWEBUI_PASSWORD}"
: "${AMAP_KEY:?set AMAP_KEY (Web服务 Key, not JS API)}"

python3 - "$OPENWEBUI_URL" <<'PY'
import json, os, sys, urllib.parse, urllib.request

base = sys.argv[1].rstrip("/")
user = os.environ["OPENWEBUI_USERNAME"]
password = os.environ["OPENWEBUI_PASSWORD"]
key = os.environ["AMAP_KEY"].strip()
if not key:
    raise SystemExit("AMAP_KEY empty")

def http_json(method, url, payload=None, token=None, timeout=30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}

def amap_get(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{q}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "0", "info": type(exc).__name__}

geo = amap_get(
    "https://restapi.amap.com/v3/geocode/geo",
    {"key": key, "address": "北京南站", "output": "JSON"},
)
geo_status = str(geo.get("status") or "")
geo_info = str(geo.get("info") or geo.get("infocode") or "")
location = ""
geos = geo.get("geocodes")
if isinstance(geos, list) and geos and isinstance(geos[0], dict):
    location = str(geos[0].get("location") or "")
dest = amap_get(
    "https://restapi.amap.com/v3/geocode/geo",
    {"key": key, "address": "北京首都国际机场", "output": "JSON"},
)
dest_loc = ""
dests = dest.get("geocodes")
if isinstance(dests, list) and dests and isinstance(dests[0], dict):
    dest_loc = str(dests[0].get("location") or "")
drive = amap_get(
    "https://restapi.amap.com/v5/direction/driving",
    {
        "key": key,
        "origin": location or "116.378319,39.865246",
        "destination": dest_loc or "116.603928,40.080111",
        "strategy": "32",
        "show_fields": "cost,tmcs,polyline",
        "output": "json",
    },
)
drive_status = str(drive.get("status") or "")
drive_info = str(drive.get("info") or drive.get("infocode") or "")
km = None
minutes = None
has_tmc = False
route = drive.get("route") if isinstance(drive.get("route"), dict) else {}
paths = route.get("paths") if isinstance(route, dict) else None
if isinstance(paths, list) and paths and isinstance(paths[0], dict):
    path = paths[0]
    try:
        km = round(float(path.get("distance") or 0) / 1000.0, 1)
    except (TypeError, ValueError):
        km = None
    cost = path.get("cost") if isinstance(path.get("cost"), dict) else {}
    try:
        minutes = int(round(float(cost.get("duration") or 0) / 60.0))
    except (TypeError, ValueError):
        minutes = None
    tmcs = path.get("tmcs")
    has_tmc = isinstance(tmcs, list) and bool(tmcs)

print(
    f"amap probe geo={geo_status}/{geo_info} drive={drive_status}/{drive_info} "
    f"km={km} minutes={minutes} tmc={has_tmc}"
)
blob = f"{geo_info} {drive_info}".upper()
if "USERKEY_PLAT_NOMATCH" in blob:
    print("hint: Key 必须是 Web服务，不是 JS API / Android / iOS")
elif "INVALID_USER_IP" in blob or "10005" in blob:
    print("hint: IP 白名单加上本机出口，现网 VPS 是 78.47.152.85")
elif "INVALID_USER_SIGNATURE" in blob or "INVALID_USER_SCODE" in blob:
    print("hint: 关掉数字签名，本工具不传 sig")
elif "INVALID_USER_KEY" in blob:
    print("hint: Key 错或过期")
if geo_status != "1" or drive_status != "1" or km is None:
    raise SystemExit("amap upstream probe failed; not writing OWUI valves")

auth = http_json(
    "POST",
    f"{base}/api/v1/auths/signin",
    {"email": user, "password": password},
)
token = auth.get("token")
if not token:
    raise SystemExit("OWUI signin failed")

current = http_json(
    "GET",
    f"{base}/api/v1/tools/id/amap_drive_route/valves",
    token=token,
)
if not isinstance(current, dict):
    current = {}
payload = {
    "AMAP_KEY": key,
    "MAX_CALLS_PER_TURN": int(current.get("MAX_CALLS_PER_TURN") or 3),
    "MAX_VIA_POINTS": int(current.get("MAX_VIA_POINTS") or 24),
}
updated = http_json(
    "POST",
    f"{base}/api/v1/tools/id/amap_drive_route/valves/update",
    payload,
    token=token,
)
if not isinstance(updated, dict):
    updated = payload
key_set = bool(str(updated.get("AMAP_KEY") or payload["AMAP_KEY"]).strip())
print(f"owui valves key_set={key_set} max_calls={payload['MAX_CALLS_PER_TURN']}")
if not key_set:
    raise SystemExit("OWUI did not store AMAP_KEY")
print("inject amap key ok")
PY
