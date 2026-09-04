# ubahnstation_info_dashboard

A CPEE-driven web application that displays real-time public transport departures, walking time, and service alerts for any Munich MVG station. The dashboard is configured entirely through CPEE Data Objects — no code changes needed to switch stations or locations.

Live dashboard: https://cpee.org/out/frames/yifei/

GitHub: https://github.com/yifei0304/ubahnstation_info_dashboard

Server: https://lehre.bpm.in.tum.de/~go93dib/

---

## Demo

**Main dashboard showing U-Bahn and Bus departures, walking time, and service alerts**

---

## System Overview

The system consists of:

- **`demo111.html`** — the display page, served from the TUM lehre server
- **`service.py`** — a lightweight Python Bottle server that proxies the Google Routes API (handles POST requests with custom headers that CPEE cannot send directly)
- **CPEE workflow** — orchestrates all data fetching and pushes results to the browser via CPEE Frames

The HTML page polls `frames.json` every 10 seconds and updates departure times, walking time, and alerts in place — the page never fully reloads.

---

## System Architecture

```
CPEE Workflow
  │
  ├── Google Geocoding API  →  coordinates for current location    (called directly from CPEE)
  ├── Google Geocoding API  →  coordinates for station             (called directly from CPEE)
  ├── service.py /route     →  walking time in minutes             (proxies Google Routes API)
  ├── MVG Departures API    →  live U-Bahn and Bus departures      (called directly from CPEE)
  ├── MVG Messages API      →  service alerts                      (called directly from CPEE)
  │
  └── CPEE Frames  →  pushes all data to demo111.html
                              │
                              └── HTML polls frames.json every 10s
                                  and updates the display in place
```

---

## Configuration

All configuration is done via **CPEE Data Objects** — nothing is hardcoded in the HTML. To switch to a different station or location, just update the values in the Data Objects tab and restart the workflow.

### Data Objects

| Name | Example Value | Description |
|------|--------------|-------------|
| `station` | `de:09162:2` | MVG global station ID. Find it via the MVG API or MVG website. |
| `station_name` | `Marienplatz(U)` | Human-readable station name, used for Google Geocoding to find station coordinates. |
| `currentlocation` | `Odeonplaz 1 München` | Address of the starting point for walking time calculation. |
| `key` | `AIzaSy...` | Google Maps API key, used for Geocoding. The key is IP-restricted to the CPEE server. |

### How to Configure

1. Open your CPEE instance
2. Go to **Data Objects** tab
3. Set `station`, `station_name`, `currentlocation`, and `key`
4. Start the workflow — the dashboard uses your values automatically

---

## CPEE Workflow Structure

The workflow follows this sequence:

```
Init → Clear → Show Header
  → [Parallel branch]
      → Get coordination current   (Geocoding API: currentlocation → lat/lng)
      → Get coordination station   (Geocoding API: station_name → lat/lng)
      → Calculate the walking time (service.py /route → walking_minute)
      → Get Departure              (MVG Departures API → ubahn, bus)
      → Get messages               (MVG Messages API → messages)
  → show Overview                  (push all data to frames)
  → [Loop: true]
      → Get Departure              (refresh departures every iteration)
      → Get messages               (refresh alerts every iteration)
      → show Overview              (update frames with fresh data)
      → Timer (15s wait)
```

### Node Descriptions

**a1 – Init:** Initialises the CPEE Frames canvas (15×15 grid). Prepare: `endpoints.init += attributes.frames_id` and `data.timeout = Time.now.to_i`.

**a7 – Clear:** Clears rows 1–14 of the frame so the dashboard page loads cleanly.

**a11 – Show Header:** Loads the TUM header into row 0 of the frame grid.

**a2 – Get coordination current:** Calls Google Geocoding API with `data.currentlocation` and `data.key`. Finalize: `data.coordination_current = result['results'][0]['geometry']['location']`.

**a14 – Get coordination station:** Calls Google Geocoding API with `data.station_name` and `data.key`. Finalize: `data.coordination_station = result['results'][0]['geometry']['location']`.

**a22 (in parallel) – Calculate the walking time:** Calls `service.py /route` with the two coordinate pairs. Finalize: `data.walking_minute = data.walking['duration'].to_i / 60`.

**a32 / a231 – Get Departure:** Calls MVG Departures API with `globalId`, `limit=50`, `transportTypes=UBAHN,BUS,REGIONAL_BUS`. Finalize filters departures by type, removes cancelled and already-departed services (30s buffer), and stores `data.ubahn` (up to 4) and `data.bus` (up to 4).

**a6 / a35 – Get messages:** Calls MVG Messages API (no parameters). Finalize filters alerts to only those relevant to the station's active lines and stores `data.messages` (up to 3).

**a22 (after parallel) / a23 (in loop) – show Overview:** PUTs all data to CPEE Frames with Type "Set UI and continue" so the loop does not block. Page Parameters: `station`, `currentlocation`, `ubahn`, `bus`, `messages`, `walkingtime`.

**Timer (a3 in loop) – 15s wait:** Pauses the loop for 15 seconds before the next refresh.

---

## Endpoints

| Name | URL | Used by |
|------|-----|---------|
| `init` | `https-post://cpee.org/out/frames/` | a1 |
| `display` | `https-put://cpee.org/out/frames/` | a7, a11, a22, a23 |
| `geocode` | `https://maps.googleapis.com/maps/api/geocode/json` | a2, a14 |
| `route` | `https://lehre.bpm.in.tum.de/ports/8081/route` | a22 (walking time) |
| `mvg_departures` | `https://www.mvg.de/api/bgw-pt/v3/departures` | a32, a231 |
| `mvg_messages` | `https://www.mvg.de/api/bgw-pt/v3/messages` | a6, a35 |
| `timeout` | `https-post://cpee.org/services/timeout.php` | Timer in loop |

---

## Page Parameters (show Overview)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `station` | `!data.station_name` | Station name shown in header |
| `currentlocation` | `!data.currentlocation` | Starting address for walking card |
| `ubahn` | `!data.ubahn` | Array of up to 4 U-Bahn departures |
| `bus` | `!data.bus` | Array of up to 4 Bus/Regional Bus departures |
| `messages` | `!data.messages` | Array of up to 3 service alerts |
| `walkingtime` | `!data.walking_minute` | Walking time in minutes (integer) |

---

## File Descriptions

| File | Purpose |
|------|---------|
| `demo111.html` | Main dashboard. Reads data from `frames.json` every 10 seconds and renders U-Bahn departures, Bus departures, walking time, and service alerts. Departed services are filtered out client-side with a 30-second buffer. |
| `service.py` | Python Bottle server on port 8081. Provides `/route` which proxies the Google Routes API POST request (JSON body + custom headers `X-Goog-Api-Key` and `X-Goog-FieldMask`) which CPEE cannot send directly. |

---

## External APIs Used

| API | Called by | Notes |
|-----|-----------|-------|
| [Google Geocoding API](https://maps.googleapis.com/maps/api/geocode/json) | CPEE a2, a14 | GET, called directly from CPEE with IP-restricted key |
| [Google Routes API](https://routes.googleapis.com/directions/v2:computeRoutes) | service.py /route | POST with JSON body and custom headers, proxied via service.py |
| [MVG Departures API](https://www.mvg.de/api/bgw-pt/v3/departures) | CPEE a32, a231 | GET, requires `globalId`, `limit`, `transportTypes` |
| [MVG Messages API](https://www.mvg.de/api/bgw-pt/v3/messages) | CPEE a6, a35 | GET, no parameters, returns all current alerts |
| [CPEE Frames](https://cpee.org/out/frames/yifei/) | CPEE display nodes | Data channel between CPEE workflow and HTML |

---

## How the Data Flow Works

**Walking time** is calculated once at startup and does not change during the session. It is pushed to `frames.json` together with the first batch of departure data.

**Departure data and alerts** are refreshed every 15 seconds by the CPEE loop. The HTML page polls `frames.json` every 10 seconds and updates only the relevant DOM elements — the page itself never reloads.

```
Startup:
  CPEE  →  Geocoding × 2  →  Routes API  →  MVG Departures  →  MVG Messages  →  frames.json
                                                                                       ↓
Loop (every 15s):                                                               HTML reads every 10s
  CPEE  →  MVG Departures  →  MVG Messages  →  frames.json                     updates DOM in place
```

Departed services are filtered out at two levels: in the CPEE Finalize script (30s buffer on server side) and again in the HTML `fetchAll()` function (30s buffer on client side).

---

## service.py Backend

The backend exists solely because the Google Routes API requires a POST request with a JSON body and custom HTTP headers (`X-Goog-Api-Key`, `X-Goog-FieldMask`, `Content-Type`) that CPEE's standard service call mechanism cannot set directly.

| Endpoint | Method | Parameters | Description |
|----------|--------|-----------|-------------|
| `/route` | GET | `olat`, `olng`, `dlat`, `dlng` | Receives coordinates, builds the Google Routes API POST request, returns `{status, duration, distanceMeters}` |

The Google API key is stored only in `service.py` on the server and is never exposed to the browser.

---

## About

Built as part of the Practical Course SS26 at i17 — Lehrstuhl für Wirtschaftsinformatik und Geschäftsprozessmanagement, TUM.
