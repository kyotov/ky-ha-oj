import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from ojmicroline_thermostat import OJMicroline, WG4API
from ojmicroline_thermostat.models import Thermostat
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from pydantic import BaseModel, field_validator

USERNAME = os.environ["THERMOSTAT_USERNAME"]
PASSWORD = os.environ["THERMOSTAT_PASSWORD"]

CACHE_TTL = int(os.environ.get("CACHE_TTL", 60))
API_PORT = int(os.environ.get("API_PORT", 8001))
API_HOST = "mythermostat.info"

REGULATION_MODES = {1: "Schedule", 2: "Comfort", 3: "Manual", 4: "Vacation", 6: "Frost Protection", 8: "Boost", 9: "Eco"}

LABELS = ["name", "serial_number"]

g_temperature          = Gauge("thermostat_temperature_fahrenheit",          "Current measured temperature (F)",                    LABELS)
g_set_point            = Gauge("thermostat_set_point_fahrenheit",            "Active target temperature (F)",                       LABELS)
g_manual_temperature   = Gauge("thermostat_manual_temperature_fahrenheit",   "Set point used in Manual mode (F)",                   LABELS)
g_comfort_temperature  = Gauge("thermostat_comfort_temperature_fahrenheit",  "Set point used in Comfort mode (F)",                  LABELS)
g_vacation_temperature = Gauge("thermostat_vacation_temperature_fahrenheit", "Set point used in Vacation mode (F)",                 LABELS)
g_min_temperature      = Gauge("thermostat_min_temperature_fahrenheit",      "Minimum allowed temperature (F)",                     LABELS)
g_max_temperature      = Gauge("thermostat_max_temperature_fahrenheit",      "Maximum allowed temperature (F)",                     LABELS)
g_heating              = Gauge("thermostat_heating",                         "1 if currently heating",                              LABELS)
g_online               = Gauge("thermostat_online",                          "1 if device is online",                               LABELS)
g_regulation_mode      = Gauge("thermostat_regulation_mode",                 "Active regulation mode (1=Schedule 2=Comfort 3=Manual 4=Vacation)", LABELS)
g_vacation_mode        = Gauge("thermostat_vacation_mode",                   "1 if vacation mode is active",                        LABELS)
g_last_primary_auto    = Gauge("thermostat_last_primary_mode_is_auto",       "1 if last primary mode was Schedule",                 LABELS)
g_comfort_end_time     = Gauge("thermostat_comfort_end_time_timestamp",      "Unix timestamp when Comfort mode expires",            LABELS)
g_vacation_begin_time  = Gauge("thermostat_vacation_begin_time_timestamp",   "Unix timestamp of vacation start",                    LABELS)
g_vacation_end_time    = Gauge("thermostat_vacation_end_time_timestamp",     "Unix timestamp of vacation end",                      LABELS)

# Read cache
_thermostats: list[Thermostat] = []
_last_updated: datetime | None = None

# Raw upstream JSON cache keyed by serial number — used for write operations
_raw: dict[str, dict] = {}

# Write session
_session_id: str | None = None
_session_calls_left: int = 0
_http: aiohttp.ClientSession | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_f(millidegrees: int) -> float:
    return round(millidegrees / 100 * 9 / 5 + 32, 1)


def from_f(fahrenheit: float) -> int:
    return round((fahrenheit - 32) * 5 / 9 * 100)


def _is_stale() -> bool:
    if _last_updated is None:
        return True
    return (datetime.now() - _last_updated).total_seconds() > CACHE_TTL


def _update_metrics(thermostats: list[Thermostat]) -> None:
    for t in thermostats:
        labels = [t.name, t.serial_number]
        g_temperature.labels(*labels).set(to_f(t.temperature))
        g_set_point.labels(*labels).set(to_f(t.set_point_temperature))
        g_manual_temperature.labels(*labels).set(to_f(t.manual_temperature))
        g_comfort_temperature.labels(*labels).set(to_f(t.comfort_temperature))
        g_vacation_temperature.labels(*labels).set(to_f(t.vacation_temperature))
        g_min_temperature.labels(*labels).set(to_f(t.min_temperature))
        g_max_temperature.labels(*labels).set(to_f(t.max_temperature))
        g_heating.labels(*labels).set(1 if t.heating else 0)
        g_online.labels(*labels).set(1 if t.online else 0)
        g_regulation_mode.labels(*labels).set(t.regulation_mode)
        g_vacation_mode.labels(*labels).set(1 if t.vacation_mode else 0)
        g_last_primary_auto.labels(*labels).set(1 if t.last_primary_mode_is_auto else 0)
        g_comfort_end_time.labels(*labels).set(t.comfort_end_time.timestamp())
        g_vacation_begin_time.labels(*labels).set(t.vacation_begin_time.timestamp())
        g_vacation_end_time.labels(*labels).set(t.vacation_end_time.timestamp())


def thermostat_to_dict(t: Thermostat) -> dict:
    return {
        "name": t.name,
        "serial_number": t.serial_number,
        "model": t.model,
        "firmware": t.software_version,
        "online": t.online,
        "heating": t.heating,
        "regulation_mode": REGULATION_MODES.get(t.regulation_mode, t.regulation_mode),
        "temperature_f": to_f(t.temperature),
        "set_point_f": to_f(t.set_point_temperature),
        "manual_temperature_f": to_f(t.manual_temperature),
        "comfort_temperature_f": to_f(t.comfort_temperature),
        "comfort_end_time": t.comfort_end_time.isoformat(),
        "min_temperature_f": to_f(t.min_temperature),
        "max_temperature_f": to_f(t.max_temperature),
        "vacation_mode": t.vacation_mode,
        "vacation_begin": t.vacation_begin_time.isoformat(),
        "vacation_end": t.vacation_end_time.isoformat(),
        "vacation_temperature_f": to_f(t.vacation_temperature),
    }


def _get_http() -> aiohttp.ClientSession:
    global _http
    if _http is None or _http.closed:
        _http = aiohttp.ClientSession()
    return _http


# ---------------------------------------------------------------------------
# Upstream API calls
# ---------------------------------------------------------------------------

async def _ensure_session() -> str:
    global _session_id, _session_calls_left
    if _session_id is None or _session_calls_left <= 0:
        r = await _get_http().post(
            f"https://{API_HOST}/api/authenticate/user",
            json={"Application": 2, "Confirm": "", "Email": USERNAME, "Password": PASSWORD},
        )
        data = await r.json()
        if data.get("ErrorCode", 1) != 0:
            raise HTTPException(status_code=503, detail="Upstream authentication failed")
        _session_id = data["SessionId"]
        _session_calls_left = 300
    _session_calls_left -= 1
    return _session_id


async def _fetch() -> None:
    global _thermostats, _last_updated, _raw
    sid = await _ensure_session()
    r = await _get_http().get(f"https://{API_HOST}/api/thermostats", params={"sessionid": sid})
    data = await r.json()

    raws = {}
    for group in data["Groups"]:
        for t in group["Thermostats"]:
            if t:
                raws[t["SerialNumber"]] = t
    _raw = raws

    async with OJMicroline(api=WG4API(username=USERNAME, password=PASSWORD)) as client:
        _thermostats = await client.get_thermostats()

    _last_updated = datetime.now()
    _update_metrics(_thermostats)
    print(f"[{_last_updated:%H:%M:%S}] Updated {len(_thermostats)} thermostats")


async def _refresh_if_stale() -> None:
    if _is_stale():
        await _fetch()


async def _post_thermostat(serial: str, overrides: dict) -> dict:
    """Merge overrides into the raw cached body and POST to upstream. Returns fresh thermostat dict."""
    if serial not in _raw:
        raise HTTPException(status_code=404, detail=f"Serial {serial} not in cache")
    sid = await _ensure_session()
    body = {**_raw[serial], **overrides}
    r = await _get_http().post(
        f"https://{API_HOST}/api/thermostat",
        params={"sessionid": sid, "serialnumber": serial},
        json=body,
    )
    result = await r.json()
    if not result.get("Success"):
        raise HTTPException(status_code=502, detail=f"Upstream rejected update for {serial}")
    # Invalidate cache so next read reflects the change
    global _last_updated
    _last_updated = None
    return result


def _find_thermostat(name: str) -> Thermostat:
    for t in _thermostats:
        if t.name.lower() == name.lower():
            return t
    raise HTTPException(status_code=404, detail=f"Thermostat '{name}' not found")


def _validate_temp(raw: int, t: Thermostat) -> None:
    if not (t.min_temperature <= raw <= t.max_temperature):
        raise HTTPException(
            status_code=400,
            detail=f"Temperature {to_f(raw)}°F out of range [{to_f(t.min_temperature)}–{to_f(t.max_temperature)}°F]",
        )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ManualRequest(BaseModel):
    temperature_f: float


class ComfortRequest(BaseModel):
    temperature_f: float
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(tz=timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("end_time must be in the future")
        return v


class VacationRequest(BaseModel):
    enabled: bool
    temperature_f: float | None = None
    begin: datetime | None = None
    end: datetime | None = None


class ModeRequest(BaseModel):
    mode: int

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, v: int) -> int:
        if v not in (1, 2, 3, 4):
            raise ValueError("mode must be 1 (Schedule), 2 (Comfort), 3 (Manual), or 4 (Vacation)")
        return v


class VacationSetpointRequest(BaseModel):
    temperature_f: float


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

async def _set_manual(t: Thermostat, temperature_f: float) -> None:
    raw = from_f(temperature_f)
    _validate_temp(raw, t)
    await _post_thermostat(t.serial_number, {"RegulationMode": 3, "ManualTemperature": raw})


async def _set_comfort(t: Thermostat, temperature_f: float, end_time: datetime) -> None:
    raw = from_f(temperature_f)
    _validate_temp(raw, t)
    end_utc = end_time.astimezone(timezone.utc)
    end_str = end_utc.strftime("%d/%m/%Y %H:%M:00 +00:00")
    await _post_thermostat(t.serial_number, {"RegulationMode": 2, "ComfortTemperature": raw, "ComfortEndTime": end_str})


async def _set_vacation(t: Thermostat, req: VacationRequest) -> None:
    if req.enabled:
        if req.temperature_f is None or req.begin is None or req.end is None:
            raise HTTPException(status_code=400, detail="temperature_f, begin, and end are required when enabled=true")
        if req.begin >= req.end:
            raise HTTPException(status_code=400, detail="begin must be before end")
        raw = from_f(req.temperature_f)
        _validate_temp(raw, t)
        begin_str = req.begin.strftime("%d/%m/%Y %H:%M:%S")
        end_str = req.end.strftime("%d/%m/%Y %H:%M:%S")
        await _post_thermostat(t.serial_number, {
            "RegulationMode": 4, "VacationEnabled": True,
            "VacationTemperature": raw, "VacationBeginDay": begin_str, "VacationEndDay": end_str,
        })
    else:
        restore = 1 if t.last_primary_mode_is_auto else 3
        await _post_thermostat(t.serial_number, {"RegulationMode": restore, "VacationEnabled": False})


async def _set_vacation_setpoint(t: Thermostat, temperature_f: float) -> None:
    """Two-step workaround: briefly activate vacation to write the setpoint, then restore."""
    raw = from_f(temperature_f)
    _validate_temp(raw, t)
    orig_mode = _raw[t.serial_number]["RegulationMode"]
    orig_vac = _raw[t.serial_number]["VacationEnabled"]
    begin = (datetime.now() + timedelta(days=365)).strftime("%d/%m/%Y 00:00:00")
    end = (datetime.now() + timedelta(days=366)).strftime("%d/%m/%Y 00:00:00")
    sid = await _ensure_session()
    # Step 1: activate vacation with new temperature
    body1 = {**_raw[t.serial_number], "RegulationMode": 4, "VacationEnabled": True,
             "VacationTemperature": raw, "VacationBeginDay": begin, "VacationEndDay": end}
    await _get_http().post(f"https://{API_HOST}/api/thermostat",
                           params={"sessionid": sid, "serialnumber": t.serial_number}, json=body1)
    # Step 2: restore original mode
    body2 = {**_raw[t.serial_number], "RegulationMode": orig_mode, "VacationEnabled": orig_vac,
             "VacationTemperature": raw, "VacationBeginDay": begin, "VacationEndDay": end}
    r = await _get_http().post(f"https://{API_HOST}/api/thermostat",
                               params={"sessionid": sid, "serialnumber": t.serial_number}, json=body2)
    result = await r.json()
    if not result.get("Success"):
        raise HTTPException(status_code=502, detail=f"Upstream rejected vacation setpoint for {t.serial_number}")
    global _last_updated
    _last_updated = None


async def _set_mode(t: Thermostat, mode: int) -> None:
    await _post_thermostat(t.serial_number, {"RegulationMode": mode})


async def _fresh_response() -> dict:
    await _fetch()
    return {"last_updated": _last_updated.isoformat(), "thermostats": [thermostat_to_dict(t) for t in _thermostats]}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

app = FastAPI(title="Thermostat API")


# --- Read endpoints ---------------------------------------------------------

@app.get("/metrics/")
async def metrics():
    await _refresh_if_stale()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/thermostats")
async def get_thermostats():
    await _refresh_if_stale()
    return {"last_updated": _last_updated.isoformat() if _last_updated else None,
            "thermostats": [thermostat_to_dict(t) for t in _thermostats]}


@app.post("/thermostats/refresh")
async def refresh_thermostats():
    return await _fresh_response()


@app.get("/thermostats/{name}")
async def get_thermostat(name: str):
    await _refresh_if_stale()
    return thermostat_to_dict(_find_thermostat(name))


# --- Write endpoints — all thermostats (must be before /{name}/ routes) ----

@app.post("/thermostats/all/manual")
async def set_all_manual(req: ManualRequest):
    await _refresh_if_stale()
    results = []
    for t in _thermostats:
        try:
            await _set_manual(t, req.temperature_f)
            results.append({"name": t.name, "success": True})
        except HTTPException as e:
            results.append({"name": t.name, "success": False, "error": e.detail})
    fresh = await _fresh_response()
    return {**fresh, "results": results}


@app.post("/thermostats/all/comfort")
async def set_all_comfort(req: ComfortRequest):
    await _refresh_if_stale()
    results = []
    for t in _thermostats:
        try:
            await _set_comfort(t, req.temperature_f, req.end_time)
            results.append({"name": t.name, "success": True})
        except HTTPException as e:
            results.append({"name": t.name, "success": False, "error": e.detail})
    fresh = await _fresh_response()
    return {**fresh, "results": results}


@app.post("/thermostats/all/vacation")
async def set_all_vacation(req: VacationRequest):
    await _refresh_if_stale()
    results = []
    for t in _thermostats:
        try:
            await _set_vacation(t, req)
            results.append({"name": t.name, "success": True})
        except HTTPException as e:
            results.append({"name": t.name, "success": False, "error": e.detail})
    fresh = await _fresh_response()
    return {**fresh, "results": results}


@app.post("/thermostats/all/vacation-setpoint")
async def set_all_vacation_setpoint(req: VacationSetpointRequest):
    await _refresh_if_stale()
    results = []
    for t in _thermostats:
        try:
            await _set_vacation_setpoint(t, req.temperature_f)
            results.append({"name": t.name, "success": True})
        except HTTPException as e:
            results.append({"name": t.name, "success": False, "error": e.detail})
    fresh = await _fresh_response()
    return {**fresh, "results": results}


@app.post("/thermostats/all/mode")
async def set_all_mode(req: ModeRequest):
    await _refresh_if_stale()
    results = []
    for t in _thermostats:
        try:
            await _set_mode(t, req.mode)
            results.append({"name": t.name, "success": True})
        except HTTPException as e:
            results.append({"name": t.name, "success": False, "error": e.detail})
    fresh = await _fresh_response()
    return {**fresh, "results": results}


# --- Write endpoints — single thermostat ------------------------------------

@app.post("/thermostats/{name}/manual")
async def set_manual(name: str, req: ManualRequest):
    await _refresh_if_stale()
    await _set_manual(_find_thermostat(name), req.temperature_f)
    return await _fresh_response()


@app.post("/thermostats/{name}/comfort")
async def set_comfort(name: str, req: ComfortRequest):
    await _refresh_if_stale()
    await _set_comfort(_find_thermostat(name), req.temperature_f, req.end_time)
    return await _fresh_response()


@app.post("/thermostats/{name}/vacation")
async def set_vacation(name: str, req: VacationRequest):
    await _refresh_if_stale()
    await _set_vacation(_find_thermostat(name), req)
    return await _fresh_response()


@app.post("/thermostats/{name}/vacation-setpoint")
async def set_vacation_setpoint(name: str, req: VacationSetpointRequest):
    await _refresh_if_stale()
    await _set_vacation_setpoint(_find_thermostat(name), req.temperature_f)
    return await _fresh_response()


@app.post("/thermostats/{name}/mode")
async def set_mode(name: str, req: ModeRequest):
    await _refresh_if_stale()
    await _set_mode(_find_thermostat(name), req.mode)
    return await _fresh_response()


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
