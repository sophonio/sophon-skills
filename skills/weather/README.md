# Weather

Current conditions, multi-day forecasts, and place-name geocoding for Sophon, powered by the
[Open-Meteo](https://open-meteo.com/) API.

Open-Meteo is **keyless** — this skill needs **no API key and no credentials**. Everything runs
over `urllib` from the standard library, so there are no dependencies. Outbound network access is
required.

Every weather tool accepts either a `location` place name (geocoded automatically) **or** explicit
`latitude` + `longitude`. If neither is supplied, the tool returns
`{"error": "provide 'location' or latitude+longitude"}`.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `weather.current` | none | Current temperature, humidity, precipitation, wind, and a text description |
| `weather.forecast` | none | Daily forecast (high/low, precipitation, description) for 1-16 days |
| `weather.geocode` | none | Search places by name and return matching coordinates |

### `weather.current`

Parameters: `location?`, `latitude?`, `longitude?`. Returns resolved coordinates, the current
observation, units, a WMO `weatherCode` with a text `description`, and the resolved `place` when a
`location` was geocoded.

### `weather.forecast`

Parameters: `location?`, `latitude?`, `longitude?`, `days?` (1-16, default 7). Returns a `forecast`
array with one entry per day: `date`, `weatherCode`, `description`, `temperatureMax`,
`temperatureMin`, `precipitationSum`.

### `weather.geocode`

Parameters: `name` (required), `count?` (1-100, default 10). Returns a `matches` array of
`{name, country, admin1, latitude, longitude}`.

## Notes

- Weather codes follow the [WMO interpretation](https://open-meteo.com/en/docs) standard; the skill
  maps each code to a short English description.
- Temperatures are in °C, wind in km/h, and precipitation in mm (Open-Meteo defaults). Each tool
  echoes the concrete `units` returned by the API.
- Timezone is resolved automatically (`timezone=auto`) from the requested coordinates.

## Trademarks

Open-Meteo is a trademark of its respective owner. This skill is an independent client and is not
affiliated with or endorsed by Open-Meteo.
