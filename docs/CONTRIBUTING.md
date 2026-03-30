# Contributing to Sensor Data Collector

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

### Prerequisites

- **Python 3.10+** for backend
- **Node.js 18+** for frontend
- **Git** for version control

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Environmental-Dashboard/sensor_data_collector.git
   cd sensor_data_collector
   ```

2. **Set up the backend:**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows
   .\venv\Scripts\Activate.ps1
   
   # macOS/Linux
   source venv/bin/activate
   
   pip install -r requirements.txt
   uvicorn app.main:app --port 8000 --reload
   ```

3. **Set up the frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Making Changes

### Code Style

**Python (Backend):**
- Follow PEP 8
- Use type hints where possible
- Write docstrings for functions

**TypeScript (Frontend):**
- Use TypeScript interfaces (no `any`)
- Prefer functional components with hooks
- Keep components focused and small

### Commit Messages

Use clear, descriptive commit messages:
```
feat: Add voltage meter sensor support
fix: Handle NaN values in Purple Air response
docs: Update README with new error types
```

### Testing

Before submitting changes:

1. **Backend:**
   - Start the backend and check `/health`
   - Test affected API endpoints
   - Check logs for errors

2. **Frontend:**
   - Run `npm run build` to check for TypeScript errors
   - Test in browser (both light and dark mode)
   - Check mobile responsiveness

## Project Structure

```
sensor_data_collector/
├── backend/           # Python FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── models/    # Pydantic models
│   │   ├── routers/   # API endpoints
│   │   └── services/  # Business logic
│   └── requirements.txt
│
├── frontend/          # React TypeScript
│   ├── src/
│   │   ├── App.tsx    # Main component
│   │   ├── api.ts     # API client
│   │   ├── types.ts   # TypeScript types
│   │   └── index.css  # Styles
│   └── package.json
│
└── README.md
```

## Adding a New Sensor Type

To add support for a new sensor type:

### 1. Backend

**a. Add to SensorType enum** (`models/sensor.py`):
```python
class SensorType(str, Enum):
    PURPLE_AIR = "purple_air"
    TEMPEST = "tempest"
    YOUR_SENSOR = "your_sensor"  # Add this
```

**b. Create request model** (`models/sensor.py`):
```python
class AddYourSensorRequest(BaseModel):
    ip_address: str
    name: str
    location: str
    upload_token: str
```

**c. Create reading model** (`models/sensor.py`):
```python
class YourSensorReading(BaseModel):
    timestamp: str
    value1: float
    value2: float
```

**d. Create service** (`services/your_sensor_service.py`):
```python
class YourSensorService:
    async def fetch_sensor_data(self, ip_address: str) -> dict:
        # Fetch from sensor
        pass
    
    def parse_sensor_response(self, data: dict) -> YourSensorReading:
        # Parse response into reading
        pass
    
    def convert_to_csv(self, reading: YourSensorReading) -> str:
        # Convert to CSV format
        pass
    
    async def push_to_endpoint(self, csv_data: str, ...) -> dict:
        # Upload to Community Hub
        pass
```

**e. Add endpoints** (`routers/sensors.py`):
```python
@router.get("/your-sensor")
async def get_your_sensors(...):
    pass

@router.post("/your-sensor")
async def add_your_sensor(request: AddYourSensorRequest, ...):
    pass
```

**f. Update SensorManager** (`services/sensor_manager.py`):
- Add service initialization in `__init__`
- Add to `add_sensor` method
- Add polling callback

### 2. Frontend

**a. Add to SensorType** (`types.ts`):
```typescript
export type SensorType = 'purple_air' | 'tempest' | 'your_sensor';
```

**b. Add request interface** (`types.ts`):
```typescript
export interface AddYourSensorRequest {
    ip_address: string;
    name: string;
    location: string;
    upload_token: string;
}
```

**c. Add API functions** (`api.ts`):
```typescript
export const getYourSensors = () =>
    api<SensorListResponse>('/api/sensors/your-sensor');

export const addYourSensor = (data: AddYourSensorRequest) =>
    api<Sensor>('/api/sensors/your-sensor', {
        method: 'POST',
        body: JSON.stringify(data)
    });
```

**d. Add tab and form** (`App.tsx`):
```typescript
const tabs: Tab[] = [
    // ...existing tabs
    {
        id: 'your_sensor',
        label: 'Your Sensor',
        icon: YourIcon,
        color: 'your-color'
    }
];
```

## Error Handling

### Backend

Use error types to classify issues:

```python
return {
    "status": "error",
    "error_type": "connection_error",  # or cloud_error, auth_error, etc.
    "error_message": "Descriptive message"
}
```

### Frontend

Show appropriate UI for each error type:
- `battery_low`: Yellow warning (expected state)
- `cloud_error`: Purple info (temporary issue)
- Other errors: Red error message

## Questions?

- Open an issue on GitHub
- Check existing documentation in `/backend/README.md` and `/frontend/README.md`

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
