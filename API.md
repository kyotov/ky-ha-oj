# OJ Microline WG4 Thermostat API Reference

Upstream host: `https://mythermostat.info`

---

## 1. Upstream API

### 1.1 Authentication

**POST** `https://mythermostat.info/api/authenticate/user`

```json
{
  "Application": 2,
  "Confirm": "",
  "Email": "user@example.com",
  "Password": "secret"
}
```

Response:
```json
{ "SessionId": "abc123...", "ErrorCode": 0 }
```

Error (wrong credentials):
```json
{ "ErrorCode": 1 }
```

Session is valid for ~300 API calls. Pass as `?sessionid=<sid>` on all subsequent requests.

---

### 1.2 Get All Thermostats

**GET** `https://mythermostat.info/api/thermostats?sessionid=<sid>`

```json
{
  "Groups": [
    {
      "GroupName": "",
      "GroupId": -1,
      "Thermostats": [ { ...thermostat object... } ]
    }
  ]
}
```

Empty thermostat slots exist in the array — filter out items with length 0.

---

### 1.3 Update a Thermostat

**POST** `https://mythermostat.info/api/thermostat?sessionid=<sid>&serialnumber=<serial>`

Body: the **complete** thermostat object (as returned by GET) with modified fields merged in.

Response:
```json
{ "Success": true }
```

> ⚠️ **Critical quirk:** The API silently ignores partial updates. If the full
> thermostat object (including the `Schedules` array) is not present, the API
> returns `Success: true` but applies no changes. Always send the full object.

> ⚠️ `Success: true` does not guarantee the change was applied — always re-fetch
> to verify if correctness is critical.

---

### 1.4 Raw Thermostat Object Fields

All temperatures are stored as **millidegrees Celsius × 100**.

```
raw = 1555  →  15.55 °C  →  60.0 °F
raw = 2111  →  21.11 °C  →  70.0 °F
raw = 2222  →  22.22 °C  →  72.0 °F

celsius    = raw / 100
fahrenheit = raw / 100 * 9/5 + 32
raw        = round((fahrenheit - 32) * 5/9 * 100)
```

#### Identity & metadata
| Field | Type | Notes |
|---|---|---|
| `SerialNumber` | string | Unique device identifier |
| `Room` | string | Display name |
| `GroupName` | string | Zone/group label |
| `GroupId` | int | Zone ID (-1 = ungrouped) |
| `SWVersion` | string | Firmware version |
| `DistributerId` | int | Unknown purpose |
| `TZOffset` | string | Local timezone offset, e.g. `"-05:00"` |

#### Status (read-only)
| Field | Type | Notes |
|---|---|---|
| `Temperature` | int | Current measured temperature |
| `SetPointTemp` | int | Active target temperature (computed, read-only) |
| `Online` | bool | Device reachability |
| `Heating` | bool | True when element is actively heating |
| `EarlyStartOfHeating` | bool | Pre-heat flag — toggling not yet verified |
| `ErrorCode` | int | 0 = no error |
| `Confirmed` | bool | Device has confirmed its settings |

#### Regulation mode
| Field | Type | Notes |
|---|---|---|
| `RegulationMode` | int | 1=Schedule 2=Comfort 3=Manual 4=Vacation |
| `VacationEnabled` | bool | True when vacation mode is active |
| `LastPrimaryModeIsAuto` | bool | True when last non-override mode was Schedule |

#### Writable setpoints
| Field | Type | Writable | Notes |
|---|---|---|---|
| `ManualTemperature` | int | Directly | Active when `RegulationMode=3` |
| `ComfortTemperature` | int | Directly | Active when `RegulationMode=2` |
| `VacationTemperature` | int | Two-step only (see §1.5) | Active when `RegulationMode=4` |

#### Temperature limits
| Field | Notes |
|---|---|
| `MinTemp` | Minimum allowed setpoint (500 = 41°F) |
| `MaxTemp` | Maximum allowed setpoint (4000 = 104°F) |

#### Comfort timing
| Field | Format |
|---|---|
| `ComfortEndTime` | `"dd/mm/yyyy HH:MM:00 +00:00"` (UTC, seconds always `:00`) |

#### Vacation timing
| Field | Format |
|---|---|
| `VacationBeginDay` | `"dd/mm/yyyy HH:MM:SS"` (local time, no offset) |
| `VacationEndDay` | `"dd/mm/yyyy HH:MM:SS"` (local time, no offset) |

#### Energy / load
| Field | Type | Notes |
|---|---|---|
| `KwhCharge` | float | Price per kWh — not yet explored |
| `LoadMeasuringActive` | bool | Whether load measurement is active |
| `LoadManuallySetWatt` | int | Manual wattage override — not yet explored |
| `LoadMeasuredWatt` | int | Last measured wattage |

#### Schedule
Array of 7 entries (one per weekday, `WeekDayGrpNo` 1–7 where 1=Mon ... 7=Sun).
Each entry has 6 events (`ScheduleType` 0–5):

```json
{
  "WeekDayGrpNo": 1,
  "Events": [
    { "ScheduleType": 0, "Clock": "06:00:00", "TempFloor": 2778, "Active": true },
    { "ScheduleType": 1, "Clock": "09:00:00", "TempFloor": 2333, "Active": true },
    { "ScheduleType": 2, "Clock": "12:00:00", "TempFloor": 2778, "Active": false },
    { "ScheduleType": 3, "Clock": "13:00:00", "TempFloor": 2333, "Active": false },
    { "ScheduleType": 4, "Clock": "17:00:00", "TempFloor": 2778, "Active": true },
    { "ScheduleType": 5, "Clock": "23:00:00", "TempFloor": 2333, "Active": true }
  ]
}
```

Inactive events (`Active: false`) are ignored at runtime. Writing schedules is **not yet verified**.

---

### 1.5 Known Quirks

#### Silent ignore on partial body
The API accepts any JSON and responds `Success: true`, but only applies changes when the **full** thermostat object is present, including the `Schedules` array. Always merge your changes into the complete object from the GET endpoint.

#### VacationTemperature two-step workaround
`VacationTemperature` cannot be set directly while in a non-vacation mode — the API returns `Success: true` but ignores the change. Required sequence:

1. POST with `RegulationMode=4`, `VacationEnabled=true`, desired `VacationTemperature`, and future `VacationBeginDay`/`VacationEndDay`
2. Immediately POST again with the original `RegulationMode` and `VacationEnabled=false`

#### ComfortEndTime format
Must include UTC offset: `"dd/mm/yyyy HH:MM:00 +00:00"`. The seconds component must be `:00`. Omitting the offset causes a silent failure.

---

## 2. Regulation Modes

| Value | Name | Description |
|---|---|---|
| 1 | Schedule | Follows the weekly `Schedules` program |
| 2 | Comfort | Holds `ComfortTemperature` until `ComfortEndTime` |
| 3 | Manual | Holds `ManualTemperature` indefinitely |
| 4 | Vacation | Holds `VacationTemperature` between vacation dates |

---

## 3. FastAPI Wrapper — Endpoints

Base URL: `http://localhost:8001`

| Method | Path | Description |
|---|---|---|
| GET | `/thermostats` | All thermostats (refreshes if cache > 60s old) |
| POST | `/thermostats/refresh` | Force cache refresh, return fresh data |
| GET | `/thermostats/{name}` | Single thermostat by name (case-insensitive) |
| GET | `/metrics/` | Prometheus scrape endpoint |
| POST | `/thermostats/all/manual` | Set manual SP on all thermostats |
| POST | `/thermostats/all/comfort` | Set comfort SP + end time on all |
| POST | `/thermostats/all/vacation` | Enable/disable vacation on all |
| POST | `/thermostats/all/vacation-setpoint` | Set vacation SP on all |
| POST | `/thermostats/all/mode` | Set regulation mode on all |
| POST | `/thermostats/{name}/manual` | Set manual SP on one thermostat |
| POST | `/thermostats/{name}/comfort` | Set comfort SP + end time on one |
| POST | `/thermostats/{name}/vacation` | Enable/disable vacation on one |
| POST | `/thermostats/{name}/vacation-setpoint` | Set vacation SP on one |
| POST | `/thermostats/{name}/mode` | Set regulation mode on one |

> **Route ordering gotcha (FastAPI):** `/thermostats/all/...` routes must be registered
> *before* `/thermostats/{name}/...` routes. FastAPI matches routes in registration order,
> so if `/{name}/` comes first it will capture `all` as the name parameter and return 404.

All write endpoints call `_fresh_response()` after the write, which forces a full re-fetch
from the thermostat API and returns `{ last_updated, thermostats }` (plus `results` for bulk
endpoints). This ensures the response always reflects the actual state after the write.

---

## 4. FastAPI Wrapper — Write Endpoint Details

### Architecture

All write endpoints share a `_post_thermostat(serial, overrides)` helper that:
1. Merges `overrides` into the cached raw upstream JSON for that thermostat
2. POSTs the full merged object to `api/thermostat?sessionid=...&serialnumber=...`
3. Invalidates `_last_updated` so the next read triggers a fresh fetch
4. Re-fetches immediately and returns the updated thermostat

This requires storing the raw upstream JSON alongside the parsed `Thermostat`
objects in a `_raw: dict[str, dict]` cache (keyed by serial number).

Temperature conversion helper (inverse of `to_f`):
```python
def from_f(fahrenheit: float) -> int:
    return round((fahrenheit - 32) * 5 / 9 * 100)
```

### Planned endpoints

#### Set manual temperature
```
POST /thermostats/{name}/manual
POST /thermostats/all/manual
Body: { "temperature_f": 65.0 }
```
- Overrides: `{"RegulationMode": 3, "ManualTemperature": from_f(...)}`
- Validate temperature is within `[MinTemp, MaxTemp]`
- No quirks — writes directly

#### Set comfort temperature + end time
```
POST /thermostats/{name}/comfort
POST /thermostats/all/comfort
Body: { "temperature_f": 70.0, "end_time": "2026-03-12T20:00:00Z" }
```
- Overrides: `{"RegulationMode": 2, "ComfortTemperature": from_f(...), "ComfortEndTime": "dd/mm/yyyy HH:MM:00 +00:00"}`
- `end_time` must be in the future
- Seconds component of `ComfortEndTime` must be forced to `:00`

#### Set vacation mode
```
POST /thermostats/{name}/vacation
POST /thermostats/all/vacation
Body: { "enabled": true, "temperature_f": 60.0, "begin": "...", "end": "..." }
      { "enabled": false }
```
- When `enabled=true`: single POST with `RegulationMode=4, VacationEnabled=true`, temperature and dates
- When `enabled=false`: POST restoring `RegulationMode` (use `LastPrimaryModeIsAuto` to decide Schedule vs Manual) with `VacationEnabled=false`
- `VacationBeginDay`/`VacationEndDay` formatted in local time without offset

#### Set vacation temperature (without activating vacation mode)
```
POST /thermostats/{name}/vacation-setpoint
POST /thermostats/all/vacation-setpoint
Body: { "temperature_f": 60.0 }
```
- Requires the two-step workaround (activate vacation → restore original mode)

#### Set regulation mode
```
POST /thermostats/{name}/mode
POST /thermostats/all/mode
Body: { "mode": 3 }
```
- Validate `mode` in `{1, 2, 3, 4}`
- For mode 2 (Comfort): use existing `ComfortEndTime` from cache or require caller to use `/comfort` endpoint
- For mode 4 (Vacation): recommend using `/vacation` endpoint instead

#### Set schedule *(unverified — stub 501)*
```
PUT /thermostats/{name}/schedule
Body: { "days": { "1": [...events...], "2": [...], ... } }
```
- Map day numbers to `WeekDayGrpNo`
- Pad to exactly 6 events per day
- Mark experimental until verified against the live API

### Bulk behaviour
All `/thermostats/all/...` endpoints iterate over all thermostats, collect per-device results, and return 207 Multi-Status if any individual request fails. Individual failures do not abort the loop.

### Error responses
| Condition | Status |
|---|---|
| Thermostat not found | 404 |
| Temperature out of range | 400 |
| Invalid mode | 400 |
| `end_time` in the past | 400 |
| Missing required field | 422 |
| Upstream `Success: false` | 502 |
| Upstream timeout | 502 |
| Upstream auth failure | 503 |

---

## 5. Not Yet Explored

- Writing `Schedules` array (7-day program) — structure is known, effect unverified
- `EarlyStartOfHeating` toggle
- `LoadManuallySetWatt` (manual wattage override)
- `KwhCharge` (electricity price per kWh)
- `DistributerId` (unknown purpose)
