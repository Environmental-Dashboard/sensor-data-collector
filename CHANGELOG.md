# Changelog

All notable changes to the Sensor Data Collector project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-01-05

### Added - Initial Release

#### Core Features
- **FastAPI Backend** - Complete REST API for sensor management
- **Purple Air Support** - Full integration with Purple Air sensors
  - Local IP-based data fetching
  - JSON to CSV conversion
  - Automatic polling every 60 seconds
  - Air quality metrics (PM1.0, PM2.5, PM10, AQI)
  - Environmental data (temperature, humidity, pressure)
  
- **Tempest Weather Support** - Full integration with WeatherFlow Tempest
  - Local network access via Hub
  - Comprehensive weather data collection
  - Temperature, humidity, pressure
  - Wind speed, gust, and direction
  - Rain accumulation
  - UV index and solar radiation
  - Lightning detection

- **Sensor Management**
  - Add sensors via REST API
  - Turn sensors on/off (start/stop polling)
  - Manual data fetch for testing
  - Real-time status tracking
  - Error reporting with last error message
  - Last active timestamp
  - Sensor-specific configuration (IP address, device ID, etc.)

- **Automatic Data Collection**
  - APScheduler-based polling system
  - Configurable polling interval (default 60 seconds)
  - Concurrent polling for multiple sensors
  - Automatic retry on failure
  - Status updates after each poll

- **CSV Export & Upload**
  - Automatic CSV conversion for all sensor types
  - Header generation
  - Timestamp inclusion
  - File upload to external endpoint
  - Bearer token authentication
  - Filename generation with timestamps

#### API Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /api/sensors` - List all sensors (with optional type filter)
- `GET /api/sensors/{id}` - Get specific sensor
- `DELETE /api/sensors/{id}` - Delete sensor
- `GET /api/sensors/{id}/status` - Get sensor status
- `POST /api/sensors/{id}/turn-on` - Start data collection
- `POST /api/sensors/{id}/turn-off` - Stop data collection
- `POST /api/sensors/{id}/fetch-now` - Manual data fetch
- `POST /api/sensors/purple-air` - Add Purple Air sensor
- `GET /api/sensors/purple-air` - List Purple Air sensors
- `POST /api/sensors/tempest` - Add Tempest sensor
- `GET /api/sensors/tempest` - List Tempest sensors
- `POST /api/test/upload/csv` - Test CSV upload (development)
- `GET /api/test/health` - Test endpoint info

#### Documentation
- **README.md** - Comprehensive project overview
  - Quick start guide
  - Architecture diagram
  - API reference
  - Configuration guide
  - Testing examples
  
- **API.md** - Complete API documentation
  - All endpoints documented
  - Request/response examples
  - Error handling guide
  - Data models
  - CSV formats
  
- **ARCHITECTURE.md** - Detailed architecture documentation
  - System overview
  - Component architecture
  - Data flow diagrams
  - Technology stack
  - Design patterns
  - Service layer details
  - Scheduling system
  - Scalability considerations
  
- **DEPLOYMENT.md** - Production deployment guide
  - Local deployment
  - Production server setup
  - Docker deployment
  - System service configuration
  - Cloud deployment (AWS, GCP, Digital Ocean)
  - Cloudflare Tunnel setup
  - Monitoring and maintenance
  - Troubleshooting
  
- **DEVELOPMENT.md** - Developer guide
  - Development setup
  - Project structure
  - Code style guide
  - Adding new sensor types (step-by-step)
  - Testing guide
  - Debugging tips
  - Git workflow
  - Contributing guidelines
  
- **INDEX.md** - Documentation index
  - Quick links
  - Topic-based organization
  - Quick reference
  - Common commands

- **FRONTEND_REQUIREMENTS.md** - Frontend implementation specs
  - Complete UI/UX specifications
  - TypeScript interfaces
  - API integration guide

#### Infrastructure
- **Environment Configuration**
  - `.env` file support via python-dotenv
  - Environment variable validation
  - Configurable polling interval
  - CORS configuration
  - External endpoint configuration

- **Error Handling**
  - Comprehensive exception handling
  - Error type classification (connection, timeout, HTTP, unknown)
  - Error message storage
  - Graceful degradation

- **Logging**
  - Startup information logging
  - Configuration display
  - Error logging
  - Shutdown logging

- **CORS Support**
  - Configurable allowed origins
  - Support for multiple frontend URLs
  - Credentials support

#### Developer Experience
- **Automatic API Documentation**
  - Swagger UI at `/docs`
  - ReDoc at `/redoc`
  - OpenAPI schema at `/openapi.json`

- **Type Hints**
  - Complete type hints throughout codebase
  - Pydantic models for validation
  - IDE autocomplete support

- **Code Organization**
  - Modular service architecture
  - Separation of concerns
  - Dependency injection
  - Repository pattern for sensor storage

#### Testing Support
- **Test Endpoint**
  - Local CSV upload endpoint for testing
  - Token-based authentication
  - File inspection and validation
  - Development/testing mode support

#### Dependencies
- FastAPI 0.109.0 - Web framework
- Uvicorn 0.27.0 - ASGI server
- HTTPX 0.26.0 - Async HTTP client
- APScheduler 3.10.4 - Background task scheduling
- Pydantic 2.5.3 - Data validation
- python-dotenv 1.0.0 - Environment management
- python-multipart 0.0.6 - File upload support

### Planned Features (Not Yet Implemented)

#### Sensor Support
- Water quality sensors
- Mayfly dataloggers

#### Frontend
- React dashboard for sensor management
- Real-time status visualization
- Historical data charts
- Configuration UI

#### Backend Enhancements
- Database persistence (currently in-memory)
- User authentication and authorization
- Rate limiting
- WebSocket support for real-time updates
- Historical data storage
- Alert system for sensor failures
- Advanced analytics

---

## [Unreleased]

### To Be Added
- [ ] Database persistence layer
- [ ] User authentication
- [ ] Rate limiting middleware
- [ ] WebSocket support
- [ ] Water quality sensor support
- [ ] Mayfly datalogger support
- [ ] React frontend dashboard
- [ ] Historical data API
- [ ] Alert system
- [ ] Docker Compose setup
- [ ] CI/CD pipeline
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance monitoring
- [ ] Grafana dashboards

---

## Version History

### [1.0.0] - 2026-01-05
Initial release with Purple Air and Tempest support, comprehensive documentation, and production-ready backend.

---

## Upgrade Notes

### Upgrading to 1.0.0
This is the initial release. No upgrade steps required.

---

## Breaking Changes

### [1.0.0]
No breaking changes (initial release).

---

## Known Issues

### [1.0.0]
- **In-Memory Storage:** Sensor configurations are lost on server restart. Database persistence planned for future release.
- **No Authentication:** Sensor management endpoints are open. Add your own authentication middleware if needed.
- **Single Instance:** Cannot run multiple backend instances simultaneously due to in-memory storage.
- **No Rate Limiting:** Consider adding rate limiting for production deployments.

---

## Migration Guide

### From Pre-Release to 1.0.0
Not applicable (initial release).

---

## Deprecation Notices

None at this time.

---

## Security Updates

### [1.0.0]
- Initial security measures implemented
- Bearer token authentication for external endpoint
- CORS configuration
- Input validation via Pydantic
- Recommend adding API authentication for production

---

## Contributors

### [1.0.0]
- **Backend Development:** Sensor Data Collector Team
- **Documentation:** Sensor Data Collector Team
- **Architecture:** Sensor Data Collector Team
- **Testing:** Sensor Data Collector Team

---

## Acknowledgments

- **FastAPI** - Excellent web framework
- **Pydantic** - Robust data validation
- **HTTPX** - Modern async HTTP client
- **APScheduler** - Reliable background task scheduling
- **Purple Air** - Air quality sensor hardware
- **WeatherFlow** - Tempest weather station hardware
- **Cloudflare** - Free tunnel service for remote access

---

## Release Process

### How to Create a Release

1. **Update Version Numbers**
   - `main.py` - Update version in API description
   - `README.md` - Update version badge/number
   - This CHANGELOG - Add new version section

2. **Update Documentation**
   - Ensure all docs reflect new features
   - Update API documentation
   - Add migration notes if needed

3. **Tag Release**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

4. **Create GitHub Release**
   - Copy changelog entry to release notes
   - Attach any relevant files
   - Publish release

5. **Announce**
   - Update project README
   - Notify users of new release
   - Share in relevant communities

---

## Support

For questions about this changelog or release notes:
- Open an issue on GitHub
- Check documentation
- Contact maintainers

---

**Last Updated:** January 5, 2026  
**Next Release:** TBD (v1.1.0 planned features: database persistence, authentication)

