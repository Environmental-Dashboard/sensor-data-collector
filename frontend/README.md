# Frontend - Sensor Dashboard

React dashboard for monitoring and controlling environmental sensors.

**Live:** https://ed-sensor-dashboard.vercel.app

## Quick Start

```powershell
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Technology Stack

- **React 18** with hooks
- **TypeScript** for type safety
- **Vite** for fast builds
- **Lucide React** for icons
- **CSS** (no framework, custom styles)

## Project Structure

```
src/
├── App.tsx        # Main component (tabs, cards, modals)
├── api.ts         # API client functions
├── types.ts       # TypeScript interfaces
├── index.css      # All styling
└── images/        # Icons, logos
```

## Components

### SensorCard

Displays a single sensor with:
- Name and location
- Status badge (active, inactive, offline, error)
- Battery voltage (if applicable)
- Error/warning messages
- Control buttons (turn on/off, fetch now)
- Options menu (edit, frequency, diagnostics)

### Status Types

| Status | Color | Icon | Description |
|--------|-------|------|-------------|
| `active` | Green | ⚡ | Polling and uploading data |
| `inactive` | Gray | ⏸ | Not polling |
| `offline` | Yellow | 🔋 | Battery low, sensor powered off |
| `error` | Red | ❌ | Something went wrong |
| `cloud_error` | Purple | ☁ | Community Hub unavailable |

### AddSensorModal

Form for adding new sensors:
- Purple Air: IP address, name, location, token
- Tempest: Device ID, location, token
- Water Quality: Device ID, Ubidots token, name, location, token

### EditSensorModal

Modify existing sensor:
- Name, location
- IP address / Device ID
- Upload token

## API Integration

All API calls are in `api.ts`:

```typescript
// Fetch sensors
const { sensors } = await getSensors();

// Add sensor
await addPurpleAirSensor({ ip_address, name, location, upload_token });

// Control sensor
await turnOnSensor(id);
await turnOffSensor(id);
await fetchSensorData(id);

// Update settings
await updateSensor(id, { name, location });
await setSensorFrequency(id, 60);
```

## Styling

All styles are in `index.css`:

### Theme Support

- Auto-detects system preference (light/dark)
- Manual toggle in header
- CSS variables for colors

### Color System

```css
--primary: #6366f1;        /* Purple - primary actions */
--success: #22c55e;        /* Green - active, success */
--warning: #f59e0b;        /* Amber - warnings, battery low */
--error: #ef4444;          /* Red - errors */
--cloud-error: #818cf8;    /* Light purple - cloud issues */
```

### Responsive Design

- Mobile-first approach
- Cards stack on small screens
- Modals adapt to screen size

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend URL (Cloudflare Tunnel) |

Set in Vercel:
1. Go to Project Settings → Environment Variables
2. Add `VITE_API_URL` = `https://your-tunnel.trycloudflare.com`
3. Redeploy

## Deployment

### To Vercel

```powershell
# Build and deploy
npm run build
vercel --prod

# Set production alias
vercel alias set <deployment-url> ed-sensor-dashboard.vercel.app
```

### Local Testing

```powershell
# Test production build locally
npm run build
npm run preview
```

## Development

### Type Safety

All API responses have TypeScript interfaces in `types.ts`:

```typescript
interface Sensor {
  id: string;
  sensor_type: SensorType;
  name: string;
  status: SensorStatus;
  status_reason: string | null;  // 'battery_low', 'cloud_error', etc.
  battery_volts: number | null;
  // ...
}
```

### Error Handling

- Toast notifications for user feedback
- Graceful degradation for API errors
- Connection status indicator in header

### Adding Features

1. Add TypeScript interfaces to `types.ts`
2. Add API functions to `api.ts`
3. Update `App.tsx` for UI changes
4. Add styles to `index.css`

## Files

| File | Purpose |
|------|---------|
| `vite.config.ts` | Vite configuration |
| `tsconfig.json` | TypeScript settings |
| `vercel.json` | Vercel deployment config |
| `.env.production` | Production environment (if needed) |
