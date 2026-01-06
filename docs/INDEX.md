# Documentation Index

Complete guide to all documentation available for the Sensor Data Collector project.

---

## Quick Links

- [**README**](../README.md) - Project overview and quick start
- [**API Reference**](API.md) - Complete API documentation
- [**Architecture**](ARCHITECTURE.md) - System design and architecture
- [**Deployment**](DEPLOYMENT.md) - Production deployment guide
- [**Development**](DEVELOPMENT.md) - Developer guide and contribution guidelines
- [**Frontend Requirements**](../frontend/FRONTEND_REQUIREMENTS.md) - Frontend implementation specs

---

## Documentation Structure

### For New Users

**Start Here:**
1. [README.md](../README.md) - Understand what the project does
2. [Quick Start Guide](../README.md#quick-start) - Get up and running in 5 minutes
3. [API.md](API.md) - Learn how to use the API

**Next Steps:**
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deploy to production
- [ARCHITECTURE.md](ARCHITECTURE.md) - Understand how it works

### For Developers

**Contributing:**
1. [DEVELOPMENT.md](DEVELOPMENT.md) - Set up development environment
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand the system
3. [API.md](API.md) - API reference for building features

**Adding Features:**
- [Adding New Sensors](DEVELOPMENT.md#adding-new-sensor-types) - Step-by-step guide
- [Code Style Guide](DEVELOPMENT.md#code-style--standards) - Formatting and conventions
- [Testing Guide](DEVELOPMENT.md#testing) - How to test your code

### For System Administrators

**Deployment:**
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
2. [Monitoring & Maintenance](DEPLOYMENT.md#monitoring--maintenance) - Keep it running
3. [Troubleshooting](DEPLOYMENT.md#troubleshooting) - Fix common issues

**Security:**
- [Security Best Practices](DEPLOYMENT.md#security-best-practices)
- [Environment Configuration](DEPLOYMENT.md#environment-configuration)

### For Frontend Developers

**Building the Dashboard:**
1. [FRONTEND_REQUIREMENTS.md](../frontend/FRONTEND_REQUIREMENTS.md) - Complete specifications
2. [API.md](API.md) - Backend API reference
3. [Data Models](API.md#data-models) - TypeScript interfaces

---

## Documentation by Topic

### Getting Started
- [Installation](../README.md#quick-start)
- [Configuration](DEPLOYMENT.md#environment-configuration)
- [First Sensor Setup](../README.md#add-your-first-sensor)
- [Verification](../README.md#monitor-your-sensors)

### Core Concepts
- [Architecture Overview](ARCHITECTURE.md#system-overview)
- [Data Flow](ARCHITECTURE.md#data-flow)
- [Sensor Types](../README.md#supported-sensors)
- [Polling System](ARCHITECTURE.md#scheduling-system)

### API Documentation
- [Endpoints Reference](API.md#endpoints)
- [Request/Response Formats](API.md#data-models)
- [Error Handling](API.md#error-handling)
- [Authentication](API.md#authentication)
- [CSV Formats](API.md#csv-formats)

### Deployment
- [Local Development](DEPLOYMENT.md#local-development-deployment)
- [Production Server](DEPLOYMENT.md#production-deployment)
- [Docker](DEPLOYMENT.md#docker-deployment)
- [System Service](DEPLOYMENT.md#system-service-deployment)
- [Cloud Deployment](DEPLOYMENT.md#cloud-deployment)
- [Cloudflare Tunnel](DEPLOYMENT.md#cloudflare-tunnel-setup)

### Development
- [Project Structure](DEVELOPMENT.md#project-structure)
- [Code Style](DEVELOPMENT.md#code-style--standards)
- [Adding Sensors](DEVELOPMENT.md#adding-new-sensor-types)
- [Testing](DEVELOPMENT.md#testing)
- [Debugging](DEVELOPMENT.md#debugging)
- [Git Workflow](DEVELOPMENT.md#git-workflow)

### Architecture
- [Component Architecture](ARCHITECTURE.md#component-architecture)
- [Technology Stack](ARCHITECTURE.md#technology-stack)
- [Design Patterns](ARCHITECTURE.md#design-patterns)
- [Service Layer](ARCHITECTURE.md#service-layer)
- [Data Models](ARCHITECTURE.md#data-models)
- [Scheduling](ARCHITECTURE.md#scheduling-system)
- [Error Handling](ARCHITECTURE.md#error-handling)
- [Security](ARCHITECTURE.md#security-considerations)
- [Scalability](ARCHITECTURE.md#scalability)

### Operations
- [Monitoring](DEPLOYMENT.md#monitoring--maintenance)
- [Logging](DEVELOPMENT.md#logging)
- [Troubleshooting](DEPLOYMENT.md#troubleshooting)
- [Backup & Recovery](DEPLOYMENT.md#backup--recovery)
- [Performance](DEVELOPMENT.md#performance-optimization)

---

## Quick Reference

### Common Commands

**Development:**
```bash
# Start dev server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Format code
black app/

# Type checking
mypy app/
```

**Production:**
```bash
# Start service
sudo systemctl start sensor-collector

# View logs
sudo journalctl -u sensor-collector -f

# Restart service
sudo systemctl restart sensor-collector

# Check status
curl http://localhost:8000/health
```

**Docker:**
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Important Files

| File | Location | Purpose |
|------|----------|---------|
| README.md | `/` | Main documentation |
| API.md | `/docs/` | API reference |
| ARCHITECTURE.md | `/docs/` | Architecture docs |
| DEPLOYMENT.md | `/docs/` | Deployment guide |
| DEVELOPMENT.md | `/docs/` | Developer guide |
| main.py | `/backend/app/` | Application entry |
| sensor_manager.py | `/backend/app/services/` | Core logic |
| sensors.py | `/backend/app/routers/` | API endpoints |
| sensor.py | `/backend/app/models/` | Data models |
| requirements.txt | `/backend/` | Dependencies |
| .env | `/backend/` | Configuration (not in git) |

### API Endpoints Quick Reference

**Sensor Management:**
- `GET /api/sensors` - List all sensors
- `POST /api/sensors/{type}` - Add sensor
- `GET /api/sensors/{id}` - Get sensor
- `DELETE /api/sensors/{id}` - Delete sensor

**Sensor Control:**
- `POST /api/sensors/{id}/turn-on` - Start polling
- `POST /api/sensors/{id}/turn-off` - Stop polling
- `POST /api/sensors/{id}/fetch-now` - Manual fetch
- `GET /api/sensors/{id}/status` - Get status

**Health:**
- `GET /` - API info
- `GET /health` - Health check
- `GET /docs` - Interactive docs

### Environment Variables Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EXTERNAL_ENDPOINT_URL` | Yes | - | CSV upload endpoint |
| `EXTERNAL_ENDPOINT_TOKEN` | Yes | - | Auth token |
| `POLLING_INTERVAL` | No | 60 | Seconds between polls |
| `FRONTEND_URL` | No | localhost:5173 | CORS origin |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |

---

## Version Information

**Current Version:** 1.0.0

**Last Updated:** January 2026

**Python Version:** 3.9+

**Key Dependencies:**
- FastAPI 0.109.0
- Uvicorn 0.27.0
- HTTPX 0.26.0
- APScheduler 3.10.4
- Pydantic 2.5.3

---

## Getting Help

### Documentation Issues
If you find errors or gaps in the documentation:
1. Open an issue on GitHub
2. Label it with `documentation`
3. Describe what needs improvement

### Technical Support
For technical questions:
1. Check relevant documentation section
2. Review [Troubleshooting](DEPLOYMENT.md#troubleshooting)
3. Search existing GitHub issues
4. Open a new issue with details

### Contributing
To contribute to documentation:
1. Follow [Development Guide](DEVELOPMENT.md)
2. Update relevant docs with your changes
3. Submit pull request

---

## Documentation Roadmap

### Planned Additions
- [ ] Video tutorials
- [ ] Docker Compose examples
- [ ] Kubernetes deployment guide
- [ ] Database integration guide
- [ ] Authentication setup guide
- [ ] Advanced monitoring with Grafana
- [ ] CI/CD pipeline examples
- [ ] Multi-sensor best practices
- [ ] Sensor simulator for testing
- [ ] API client libraries

### Recently Added
- ✅ Complete API reference
- ✅ Architecture documentation
- ✅ Deployment guide
- ✅ Development guide
- ✅ Frontend requirements

---

## External Resources

### Technologies Used
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [HTTPX Documentation](https://www.python-httpx.org/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Uvicorn Documentation](https://www.uvicorn.org/)

### Sensor Documentation
- [Purple Air Local API](https://community.purpleair.com/t/local-api-documentation/158)
- [WeatherFlow Tempest API](https://weatherflow.github.io/Tempest/)
- [Cloudflare Tunnel Setup](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

### Python Resources
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Async/Await in Python](https://docs.python.org/3/library/asyncio.html)
- [PEP 8 Style Guide](https://pep8.org/)

---

## Feedback

We welcome feedback on our documentation! Please:
- Open GitHub issues for errors or improvements
- Submit pull requests for fixes
- Share your experience in discussions

**Thank you for using Sensor Data Collector!**

---

**Last Updated:** January 2026  
**Maintained by:** Sensor Data Collector Team

