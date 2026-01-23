# Sensor Data Collector - System Architecture

A comprehensive overview of the system architecture with visual diagrams.

---

## 🌐 System Overview

How all components connect together - from physical sensors to the cloud.

```mermaid
flowchart TB
    subgraph Physical [Physical Layer]
        direction LR
        PA1[Purple Air 001<br/>10.17.192.161]
        PA2[Purple Air 002<br/>10.17.192.162]
        PA3[Purple Air 003<br/>10.17.192.163]
        TM[Tempest Weather<br/>Device 205498]
        VM[Voltage Meter ESP32<br/>10.17.196.250]
        BAT[12V LiFePO4<br/>Battery]
    end

    subgraph Backend [Backend Server - Local Machine]
        direction TB
        MAIN[FastAPI App<br/>main.py]
        SM[Sensor Manager<br/>The Brain]
        SCH[APScheduler<br/>Polling Timer]
        
        subgraph Services [Service Layer]
            PAS[Purple Air<br/>Service]
            TMS[Tempest<br/>Service]
            VMS[Voltage Meter<br/>Service]
        end
    end

    subgraph Cloud [Cloud Services]
        CH[Community Hub<br/>oberlin.communityhub.cloud]
        VCL[Vercel<br/>Frontend Hosting]
        CFT[Cloudflare Tunnel<br/>Secure Access]
    end

    subgraph Client [End Users]
        WEB[Web Browser]
        DASH[Dashboard UI]
    end

    BAT --> VM
    VM -->|Controls Power| PA2
    
    PA1 & PA2 & PA3 -->|HTTP /json| PAS
    TM -->|WebSocket| TMS
    VM -->|HTTP /status.json| VMS
    
    MAIN --> SM
    SCH --> SM
    SM --> PAS & TMS & VMS
    
    PAS & TMS & VMS -->|Upload CSV| CH
    
    WEB --> VCL
    VCL --> DASH
    DASH <-->|API Calls| CFT
    CFT <-->|Tunnel| MAIN
```

---

## 🔋 Power Saving Mode Flow

How the system conserves battery by cycling power to sensors.

```mermaid
flowchart TD
    subgraph Scheduler [APScheduler Jobs]
        PREWAKE[Pre-Wake Job<br/>Runs 30s before poll]
        POLL[Poll Job<br/>Main data collection]
    end

    subgraph PowerCycle [Power Saving Cycle]
        A[Sensor SLEEPING<br/>Relay OFF] -->|30s before poll| B[Pre-Wake Triggered]
        B --> C[Turn Relay ON<br/>Status: WAKING]
        C --> D[Wait for WiFi<br/>~25 seconds]
        D --> E[Poll Triggered<br/>Fetch Data]
        E --> F{Fetch OK?}
        F -->|Yes| G[Upload to Cloud]
        G --> H[Turn Relay OFF<br/>Status: SLEEPING]
        H --> A
        
        F -->|No| I[Check Voltage Meter]
        I --> J{Relay ON?}
        J -->|No| K[Status: OFFLINE<br/>Reason: battery_low]
        J -->|Yes| L[Status: ERROR<br/>Reason: wifi_error]
    end

    PREWAKE -.-> B
    POLL -.-> E
```

---

## 📊 Status State Machine

All possible sensor states and their transitions.

```mermaid
stateDiagram-v2
    [*] --> Inactive: Sensor Added
    
    Inactive --> Active: Turn On<br/>Normal Mode
    Inactive --> Sleeping: Turn On<br/>Power Saving Mode
    
    state PowerSaving {
        Sleeping --> Waking: Pre-Wake<br/>30s before poll
        Waking --> Active: WiFi Connected
        Active --> Sleeping: Data Sent<br/>Relay OFF
    }
    
    Active --> Active: Poll Success<br/>Normal Mode
    
    Active --> Error: Fetch/Upload Failed
    Waking --> Error: WiFi Timeout
    Waking --> Offline: Battery Low
    
    Error --> Active: Retry Success
    Offline --> Waking: Battery Recovered
    
    Active --> Inactive: Turn Off
    Sleeping --> Inactive: Turn Off
    Error --> Inactive: Turn Off
```

---

## 🔄 Data Flow Sequence

The journey of data from sensor to cloud.

```mermaid
sequenceDiagram
    autonumber
    
    participant SCH as Scheduler
    participant SM as SensorManager
    participant VMS as VoltageMeterService
    participant VM as Voltage Meter ESP32
    participant PAS as PurpleAirService
    participant PA as Purple Air Sensor
    participant CH as Community Hub
    
    Note over SCH,CH: Power Saving Mode - Full Cycle
    
    rect rgb(50, 50, 80)
        Note right of SCH: Pre-Wake Phase
        SCH->>SM: Pre-wake trigger (30s early)
        SM->>VMS: set_relay(ON)
        VMS->>VM: GET /relay?on=1
        VM-->>VMS: OK
        SM->>SM: status = WAKING
    end
    
    Note over PA: Sensor boots...<br/>~25 seconds
    
    rect rgb(50, 80, 50)
        Note right of SCH: Data Collection Phase
        SCH->>SM: Poll trigger
        SM->>PAS: fetch_and_push()
        PAS->>PA: GET /json
        PA-->>PAS: JSON sensor data
        PAS->>PAS: Convert to CSV
        PAS->>CH: POST /api/data-hub/upload/csv
        CH-->>PAS: 200 OK
        PAS-->>SM: Success + reading
    end
    
    rect rgb(80, 50, 50)
        Note right of SCH: Power Down Phase
        SM->>VMS: set_relay(OFF)
        VMS->>VM: GET /relay?on=0
        VM-->>VMS: OK
        SM->>SM: status = SLEEPING
    end
```

---

## 🏗️ Backend Components

Class diagram showing the backend service architecture.

```mermaid
classDiagram
    class SensorManager {
        -sensors: Dict
        -scheduler: AsyncIOScheduler
        -purple_air_service: PurpleAirService
        -tempest_service: TempestService
        -voltage_meter_service: VoltageMeterService
        +add_purple_air_sensor()
        +add_tempest_sensor()
        +add_voltage_meter_sensor()
        +turn_on_sensor()
        +turn_off_sensor()
        +set_power_mode()
        +trigger_fetch_now()
        -_poll_purple_air_sensor()
        -_poll_tempest_sensor()
        -_poll_voltage_meter()
        -_pre_wake_sensor()
        -_find_voltage_meter_for_sensor()
        -_enhance_error_with_voltage_meter_status()
    }
    
    class PurpleAirService {
        -http_client: AsyncClient
        +fetch_data(ip_address)
        +fetch_and_push(ip, name, token)
        +push_to_endpoint(csv, name, token)
        -create_csv_row(reading)
        -csv_header()
    }
    
    class TempestService {
        -http_client: AsyncClient
        +connect_websocket(device_id)
        +fetch_and_push(ip, device_id, name, token)
        +push_to_endpoint(csv, name, token)
        -create_csv_row(observation)
    }
    
    class VoltageMeterService {
        -http_client: AsyncClient
        +get_status(ip_address)
        +set_relay(ip, on)
        +set_auto_mode(ip, auto)
        +set_thresholds(ip, lower, upper)
        +calibrate(ip, target_voltage)
        +fetch_and_push(ip, name, token)
    }
    
    class FastAPI {
        +sensors_router
        +lifespan()
        +root()
        +health()
    }
    
    SensorManager --> PurpleAirService
    SensorManager --> TempestService
    SensorManager --> VoltageMeterService
    FastAPI --> SensorManager
```

---

## 🔍 Smart Error Detection

How the system determines the cause of sensor failures.

```mermaid
flowchart TD
    A[Sensor Fetch Failed] --> B{Has linked<br/>Voltage Meter?}
    
    B -->|No| C[Generic Error<br/>Status: ERROR]
    
    B -->|Yes| D[Query Voltage Meter<br/>GET /status.json]
    D --> E{Response OK?}
    
    E -->|No| F[Cannot determine cause<br/>Status: ERROR]
    
    E -->|Yes| G{Relay ON?}
    
    G -->|No| H[Battery Low<br/>Voltage below cutoff]
    H --> I[Status: OFFLINE<br/>Reason: battery_low]
    I --> J[Message:<br/>Battery Low - Sensor powered off]
    
    G -->|Yes| K[Power is ON but<br/>sensor not responding]
    K --> L[Status: ERROR<br/>Reason: wifi_error]
    L --> M[Message:<br/>WiFi/Network Error]
    
    style I fill:#f59e0b,color:#000
    style L fill:#dc2626,color:#fff
```

---

## 📡 ESP32 Voltage Meter API

The endpoints available on the Battery Cutoff Monitor.

```mermaid
flowchart LR
    subgraph ESP32 [ESP32 Voltage Meter]
        direction TB
        STATUS[/status.json<br/>GET]
        RELAY[/relay<br/>GET]
        SETTINGS[/settings<br/>GET]
    end
    
    subgraph StatusResponse [Status Response]
        V[voltage_v: 12.5]
        L[load_on: true]
        A[auto_mode: true]
        C[v_cutoff: 11.0]
        R[v_reconnect: 12.9]
    end
    
    subgraph RelayParams [Relay Parameters]
        ON[on=1 Turn ON]
        OFF[on=0 Turn OFF]
        AUTO[auto=1 Auto Mode]
    end
    
    subgraph SettingsParams [Settings Parameters]
        LOWER[lower=11.0 Cutoff]
        UPPER[upper=12.9 Reconnect]
        TARGET[target=13.5 Calibrate]
    end
    
    STATUS --> StatusResponse
    RELAY --> RelayParams
    SETTINGS --> SettingsParams
```

---

## 🖥️ Frontend Component Flow

How the React frontend displays sensor data.

```mermaid
flowchart TD
    subgraph App [App.tsx]
        FETCH[fetchSensors<br/>useEffect]
        STATE[sensors state<br/>useState]
        TABS[Tab Navigation]
    end
    
    subgraph Cards [Sensor Cards]
        PA[Purple Air Card]
        TM[Tempest Card]
        VM[Voltage Meter Card]
    end
    
    subgraph StatusBadges [Status Indicators]
        ACTIVE[Active<br/>Power icon]
        SLEEP[Sleeping<br/>Moon icon]
        WAKE[Waking<br/>Sunrise icon]
        BATT[Battery Low<br/>Battery icon]
        ERR[Error<br/>X icon]
    end
    
    subgraph Actions [User Actions]
        TURN_ON[Turn On]
        TURN_OFF[Turn Off]
        FETCH_NOW[Fetch Now]
        DELETE[Delete]
    end
    
    FETCH -->|GET /api/sensors| STATE
    STATE --> TABS
    TABS --> PA & TM & VM
    PA & TM & VM --> StatusBadges
    PA & TM & VM --> Actions
    Actions -->|POST /api/sensors/...| FETCH
```

---

## 📁 Project Structure

```
sensor_data_collector/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── models/
│   │   │   └── sensor.py           # Pydantic models
│   │   ├── routers/
│   │   │   └── sensors.py          # API endpoints
│   │   └── services/
│   │       ├── sensor_manager.py   # The Brain
│   │       ├── purple_air_service.py
│   │       ├── tempest_service.py
│   │       └── voltage_meter_service.py
│   ├── sensors_db.json             # Persistent storage
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main component
│   │   ├── api.ts                  # API client
│   │   ├── types.ts                # TypeScript types
│   │   └── index.css               # Styles
│   └── package.json
│
├── docs/
│   └── ARCHITECTURE.md             # Detailed docs
│
├── ARCHITECTURES.md                # This file!
└── README.md
```

---

## 🔑 Key Concepts

| Concept | Description |
|---------|-------------|
| **Power Saving Mode** | Cycles relay to conserve battery - sensor sleeps between polls |
| **Pre-Wake** | Turns relay ON 30 seconds early so sensor can boot and connect WiFi |
| **Smart Error Detection** | Checks voltage meter to distinguish battery_low vs wifi_error |
| **Status Reason** | Additional context for why sensor is in current state |
| **Linked Sensor** | Voltage Meter can be linked to a Purple Air sensor to control its power |

---

## 📈 Timing Diagram

```mermaid
gantt
    title Power Saving Mode Timing
    dateFormat ss
    axisFormat %S

    section Relay
    OFF (Sleeping)     :done, sleep1, 00, 30s
    ON (Waking)        :active, wake, after sleep1, 30s
    OFF (Sleeping)     :done, sleep2, after wake, 30s

    section Sensor
    Powered Off        :done, off1, 00, 30s
    Booting            :crit, boot, after off1, 25s
    Connected          :active, conn, after boot, 5s
    Powered Off        :done, off2, after conn, 30s

    section Data
    Waiting            :done, wait, 00, 55s
    Fetch + Upload     :active, fetch, after wait, 5s
    Waiting            :done, wait2, after fetch, 30s
```

---

*Generated for Sensor Data Collector - Environmental Dashboard*
