# CSV Format Documentation

This document describes the CSV format expected by Community Hub for each sensor type.

## General Requirements

- **Encoding**: UTF-8
- **Line Endings**: Unix-style (`\n`)
- **Header Row**: Required (first line)
- **Data Row**: One row per file (single timestamp)
- **Timestamp Format**: ISO 8601 UTC (e.g., `2026-01-08T19:57:01+00:00`)

## Purple Air Sensors

### Header
```
Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),PM10.0 :cf_1( µg/m³),PM2.5 AQI
```

### Data Row Format
```
2026-01-08T19:57:01+00:00,59.0,43.0,37.0,987.82,2.91,4.74,5.11,20
```

### Fields
| Field | Type | Description |
|-------|------|-------------|
| Timestamp | ISO 8601 UTC | When reading was taken |
| Temperature (°F) | Float | Temperature in Fahrenheit |
| Humidity (%) | Float | Relative humidity (0-100) |
| Dewpoint (°F) | Float | Dewpoint temperature |
| Pressure (hPa) | Float | Atmospheric pressure |
| PM1.0 :cf_1( µg/m³) | Float | PM1.0 particles |
| PM2.5 :cf_1( µg/m³) | Float | PM2.5 particles (most important) |
| PM10.0 :cf_1( µg/m³) | Float | PM10 particles |
| PM2.5 AQI | Integer | Air Quality Index (0-500) |

### Example File
```csv
Timestamp,Temperature (°F),Humidity (%),Dewpoint (°F),Pressure (hPa),PM1.0 :cf_1( µg/m³),PM2.5 :cf_1( µg/m³),PM10.0 :cf_1( µg/m³),PM2.5 AQI
2026-01-08T19:57:01+00:00,59.0,43.0,37.0,987.82,2.91,4.74,5.11,20
```

---

## Tempest Weather Station

### Header
```
Timestamp (UTC),Temperature (°C),Temperature (°F),Humidity (%),Wind Avg (m/s),Wind Avg (mph),Wind Gust (m/s),Wind Gust (mph),Wind Lull (m/s),Wind Lull (mph),Wind Direction (°),Pressure (mb),Pressure (inHg),UV Index,Solar Radiation (W/m²),Illuminance (lux),Rain (mm),Rain (in),Precip Type,Lightning Count,Lightning Distance (km),Lightning Distance (mi),Battery (V),Report Interval (min)
```

### Data Row Format
```
2026-01-08T19:57:01Z,15.0,59.0,43.0,2.5,5.6,3.2,7.2,1.8,4.0,180,987.82,29.18,2.5,150.0,5000,0.0,0.0000,0,0,0.0,0.0,2.7,1
```

### Fields
| Field | Type | Description |
|-------|------|-------------|
| Timestamp (UTC) | ISO 8601 UTC | When reading was taken |
| Temperature (°C) | Float | Temperature in Celsius |
| Temperature (°F) | Float | Temperature in Fahrenheit |
| Humidity (%) | Float | Relative humidity (0-100) |
| Wind Avg (m/s) | Float | Average wind speed (m/s) |
| Wind Avg (mph) | Float | Average wind speed (mph) |
| Wind Gust (m/s) | Float | Wind gust speed (m/s) |
| Wind Gust (mph) | Float | Wind gust speed (mph) |
| Wind Lull (m/s) | Float | Wind lull/minimum (m/s) |
| Wind Lull (mph) | Float | Wind lull/minimum (mph) |
| Wind Direction (°) | Integer | Wind direction (0-360) |
| Pressure (mb) | Float | Station pressure (millibars) |
| Pressure (inHg) | Float | Station pressure (inches Hg) |
| UV Index | Float | UV radiation level |
| Solar Radiation (W/m²) | Float | Solar radiation |
| Illuminance (lux) | Float | Light level |
| Rain (mm) | Float | Rain accumulated (mm) |
| Rain (in) | Float | Rain accumulated (inches) |
| Precip Type | Integer | 0=None, 1=Rain, 2=Hail, 3=Mix |
| Lightning Count | Integer | Number of strikes |
| Lightning Distance (km) | Float | Average distance (km) |
| Lightning Distance (mi) | Float | Average distance (miles) |
| Battery (V) | Float | Battery voltage |
| Report Interval (min) | Integer | Report interval |

### Example File
```csv
Timestamp (UTC),Temperature (°C),Temperature (°F),Humidity (%),Wind Avg (m/s),Wind Avg (mph),Wind Gust (m/s),Wind Gust (mph),Wind Lull (m/s),Wind Lull (mph),Wind Direction (°),Pressure (mb),Pressure (inHg),UV Index,Solar Radiation (W/m²),Illuminance (lux),Rain (mm),Rain (in),Precip Type,Lightning Count,Lightning Distance (km),Lightning Distance (mi),Battery (V),Report Interval (min)
2026-01-08T19:57:01Z,15.0,59.0,43.0,2.5,5.6,3.2,7.2,1.8,4.0,180,987.82,29.18,2.5,150.0,5000,0.0,0.0000,0,0,0.0,0.0,2.7,1
```

---

## Water Quality Sensors (Ubidots)

### Header
```
Timestamp,Water Temp (°C),Dissolved O2 (mg/L),Dissolved O2 Sat (%),Specific Conductivity (µS/cm),Turbidity (NTU),Water Level (m),Battery Voltage (V),Enclosure Temp (°C),Enclosure Humidity (%)
```

### Data Row Format
```
2026-01-08T19:57:01+00:00,15.5,8.2,85.0,250.0,5.0,1.2,3.7,20.0,45.0
```

### Fields
| Field | Type | Description |
|-------|------|-------------|
| Timestamp | ISO 8601 UTC | When reading was taken |
| Water Temp (°C) | Float | Water temperature |
| Dissolved O2 (mg/L) | Float | Dissolved oxygen concentration |
| Dissolved O2 Sat (%) | Float | Dissolved oxygen saturation |
| Specific Conductivity (µS/cm) | Float | Electrical conductivity |
| Turbidity (NTU) | Float | Water clarity |
| Water Level (m) | Float | Water level/depth |
| Battery Voltage (V) | Float | Sensor battery voltage |
| Enclosure Temp (°C) | Float | Enclosure temperature |
| Enclosure Humidity (%) | Float | Enclosure humidity |

### Example File
```csv
Timestamp,Water Temp (°C),Dissolved O2 (mg/L),Dissolved O2 Sat (%),Specific Conductivity (µS/cm),Turbidity (NTU),Water Level (m),Battery Voltage (V),Enclosure Temp (°C),Enclosure Humidity (%)
2026-01-08T19:57:01+00:00,15.5,8.2,85.0,250.0,5.0,1.2,3.7,20.0,45.0
```

---

## Upload Requirements

### HTTP Request Format

**Endpoint:** `https://oberlin.communityhub.cloud/api/data-hub/upload/csv`

**Method:** `POST`

**Headers:**
```
user-token: YOUR_UPLOAD_TOKEN
```

**Body:** `multipart/form-data`
- Field name: `file`
- Content-Type: `text/csv`
- Filename: `{sensor_name}_{timestamp}.csv`

### Response

**Success (200 OK):**
```json
{
  "status": "success",
  "filename": "SensorName_20260108_195701.csv"
}
```

**Error (400/401/500):**
- Check response body for error details
- Common errors:
  - Invalid token (401)
  - CSV format mismatch (400)
  - Server error (500)

---

## Validation Checklist

Before uploading, verify:

- [ ] CSV has exactly 2 lines (header + 1 data row)
- [ ] Header matches exactly (case-sensitive, including spaces)
- [ ] Timestamp is ISO 8601 UTC format
- [ ] All numeric values are valid floats/integers
- [ ] No trailing commas
- [ ] File encoding is UTF-8
- [ ] Filename format: `{sensor_name}_{YYYYMMDD}_{HHMMSS}.csv`

---

## Troubleshooting CSV Issues

### "CSV format mismatch" error

1. **Check header exactly matches** - Copy header from this document
2. **Verify column count** - Header and data row must have same number of columns
3. **Check for hidden characters** - Ensure no BOM or special characters
4. **Validate timestamp format** - Must be ISO 8601 UTC

### "Empty file" error

- Ensure CSV has at least header + 1 data row
- Check file is not empty or whitespace-only

### "Invalid token" error

- Verify token is correct
- Check token hasn't expired
- Ensure using `user-token` header (not `Authorization`)

---

## Testing CSV Format

Use the upload test endpoint to verify format:

```powershell
curl "http://localhost:8000/api/sensors/health/upload-test?upload_token=YOUR_TOKEN"
```

This sends a minimal test CSV and returns detailed diagnostics.
