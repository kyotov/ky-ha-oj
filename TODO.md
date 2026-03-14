# TODO

## Backend

- [ ] Validate temperature is within `[MinTemp, MaxTemp]` on write endpoints
- [ ] Return `207 Multi-Status` (not `200`) when any bulk operation partially fails
- [ ] Schedule endpoint — `PUT /thermostats/{name}/schedule` — structure is known but unverified against live API
- [ ] Explore `EarlyStartOfHeating` toggle
- [ ] Explore `LoadManuallySetWatt` (manual wattage override)
- [ ] Explore `KwhCharge` (electricity price per kWh)

## Frontend

- [ ] Bulk "All" controls: pre-fill from first thermostat's values (currently defaults to 68°F)
- [ ] Show per-thermostat error details when a bulk operation partially fails
- [ ] Schedule editor UI (once backend endpoint is verified)

## Infrastructure

- [ ] CI pipeline: build + push image on push to main
- [ ] Pin image tag to a digest or version instead of `latest`
