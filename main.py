import os
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from ojmicroline_thermostat import OJMicroline, WG4API
from ojmicroline_thermostat.models import Thermostat
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

USERNAME = os.environ["THERMOSTAT_USERNAME"]
PASSWORD = os.environ["THERMOSTAT_PASSWORD"]

CACHE_TTL = int(os.environ.get("CACHE_TTL", 60))
API_PORT = int(os.environ.get("API_PORT", 8001))

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

# Shared state
_thermostats: list[Thermostat] = []
_last_updated: datetime | None = None


def to_f(millidegrees: int) -> float:
    return round(millidegrees / 100 * 9 / 5 + 32, 1)


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


async def _fetch() -> None:
    global _thermostats, _last_updated
    async with OJMicroline(api=WG4API(username=USERNAME, password=PASSWORD)) as client:
        _thermostats = await client.get_thermostats()
    _last_updated = datetime.now()
    _update_metrics(_thermostats)
    print(f"[{_last_updated:%H:%M:%S}] Updated {len(_thermostats)} thermostats")


async def _refresh_if_stale() -> None:
    if _is_stale():
        await _fetch()


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


FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

app = FastAPI(title="Thermostat API")


@app.get("/metrics/")
async def metrics():
    await _refresh_if_stale()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/thermostats")
async def get_thermostats():
    await _refresh_if_stale()
    return {
        "last_updated": _last_updated.isoformat() if _last_updated else None,
        "thermostats": [thermostat_to_dict(t) for t in _thermostats],
    }


@app.post("/thermostats/refresh")
async def refresh_thermostats():
    await _fetch()
    return {
        "last_updated": _last_updated.isoformat(),
        "thermostats": [thermostat_to_dict(t) for t in _thermostats],
    }


@app.get("/thermostats/{name}")
async def get_thermostat(name: str):
    await _refresh_if_stale()
    for t in _thermostats:
        if t.name.lower() == name.lower():
            return thermostat_to_dict(t)
    raise HTTPException(status_code=404, detail=f"Thermostat '{name}' not found")


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
