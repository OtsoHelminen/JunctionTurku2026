# Data Consolidator

FastAPI server that serves generated weather + estate events (schema: `data_template.json`).

```bash
uv sync
cd data_consolidator
$DATA_INTERVAL_SECONDS=60 
uv run uvicorn main:app --reload   # interval defaults to 60 s
```

# API Endpoints

**Base URL:** `http://localhost:8000`

| Method | Endpoint | Description | Required Payload / Parameters |
| --- | --- | --- | --- |
| GET | `/app/data_events` | Get the latest generated data events. | None |
| GET | `/app/simulate/storm` | Trigger a storm simulation of 30 events. | None |
| GET | `/app/houses` | Retrieve all registered houses. | None |
| POST | `/app/houses` | Create a new house. | JSON body (see below). |
| GET | `/app/data_events/{house_id}` | Get data events associated with a specific house. | Path parameter: `house_id` (integer). |
| POST | `/app/devices` | Register a device for push notifications. | JSON body (see below). |
| DELETE | `/app/devices?token={token}` | Unregister a device. | Query parameter: `token` (string). |
| POST | `/app/notify/{token}` | Send a push notification to one registered device. | Path parameter: `token`; optional JSON body. |
| POST | `/app/notify` | Send a push notification to all registered devices. | Optional JSON body. |

## 1\. Create a House

**Endpoint:** `POST /app/houses`

**Required JSON payload:**

```
{
  "user_id": "user-123",
  "address": "Example Street 5",
  "latitude": 60.21,
  "longitude": 24.95
}
```

**Optional fields:**

- `construction_year` (integer)
- `house_type` (string)
- `floor_area_m2` (number)
- `number_of_floors` (integer)
- `condition` (string)

## 2\. Register a Device

**Endpoint:** `POST /app/devices`

**Required JSON payload:**

```
{
  "token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
  "platform": "ios"
}
```

- `token`: Required Expo push token.
- `platform`: Optional; accepted values are `ios` or `android`.

## 3\. Send a Push Notification

**Endpoints:**

- `POST /app/notify` — Send to all registered devices.
- `POST /app/notify/{token}` — Send to one registered device.

**Optional JSON payload:**

```
{
  "title": "Data updated",
  "body": "New data is available.",
  "sound": "default",
  "data": {
    "type": "weather_update"
  }
}
```

All payload fields are optional. If omitted, the server uses the default notification values.

## Database (SQLite)

The `db/` folder holds an SQLite database (`db/consolidator.db`, created on
first use; override with `DATABASE_PATH`) with two tables:

- **houses** — tracked estates with their location (latitude/longitude).
- **alerts** — warnings derived from a house's weather forecast
  (`heavy_rain` ≥ 10 mm, `storm_wind` ≥ 15 m/s).

The server seeds the generated estate as a house on startup. Endpoints:

Seed manually: `python -m db.seed`