# PulseCheck Backend

A robust, real-time uptime monitoring service built with FastAPI, PostgreSQL, and Redis. Monitor your websites and APIs with instant notifications and live status updates.

## 🚀 Features

### Core Monitoring
- **Real-time Uptime Monitoring** - Continuous monitoring of HTTP/HTTPS endpoints
- **Configurable Check Intervals** - Set custom monitoring intervals (30 seconds to 1 hour)
- **Multi-status Detection** - UP, DOWN, and UNKNOWN states with detailed error reporting
- **Response Time Tracking** - Monitor latency and performance metrics

### Real-time Updates
- **WebSocket Integration** - Live status updates without page refresh
- **Redis Pub/Sub** - Scalable real-time messaging architecture
- **Dashboard Broadcasting** - Real-time updates across multiple connected clients

### Smart Notifications
- **Email Alerts** - Instant notifications when services go down
- **Alert Debouncing** - Prevent notification spam with configurable cooldown periods
- **Recovery Notifications** - Get notified when services come back online
- **Postmark Integration** - Reliable email delivery with professional templates

### User Management
- **FastAPI Users Integration** - Complete authentication system
- **JWT Token Authentication** - Secure API access
- **User Registration & Login** - Full user lifecycle management
- **Multi-user Support** - Isolated monitoring for different users

### Developer Experience
- **Async/Await Architecture** - High-performance asynchronous operations
- **SQLModel ORM** - Type-safe database operations
- **Alembic Migrations** - Version-controlled database schema changes
- **Comprehensive API Documentation** - Auto-generated OpenAPI/Swagger docs
- **Docker Support** - Container-ready deployment

## 🛠️ Tech Stack

### Backend Framework
- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - Lightning-fast ASGI server
- **Pydantic** - Data validation using Python type annotations

### Database & Caching
- **PostgreSQL** - Reliable relational database with UUID support
- **Redis** - In-memory data structure store for pub/sub and caching
- **SQLModel** - SQL databases using Python type annotations
- **Alembic** - Database migration tool

### Authentication & Security
- **FastAPI Users** - Complete user authentication system
- **JWT Tokens** - Secure authentication with configurable expiration
- **Argon2** - Secure password hashing
- **CORS Middleware** - Cross-origin resource sharing support

### Monitoring & Communication
- **HTTPX** - Modern HTTP client for uptime checks
- **WebSockets** - Real-time bidirectional communication
- **Redis Pub/Sub** - Scalable message broadcasting
- **Postmark** - Professional email delivery service

### Development & Deployment
- **Docker & Docker Compose** - Containerized development and deployment
- **Pytest** - Comprehensive testing framework
- **Black & Ruff** - Code formatting and linting
- **Pre-commit Hooks** - Automated code quality checks

## 📦 Installation

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pulsecheck-backend.git
   cd pulsecheck-backend
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. **Prerequisites**
   - Python 3.12+
   - PostgreSQL 15+
   - Redis 7+

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/pulsecheck"
   export REDIS_URL="redis://localhost:6379"
   export SECRET_KEY="your-secret-key"
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

## ⚙️ Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/pulsecheck

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30 days

# Email (Optional)
POSTMARK_API_TOKEN=your-postmark-token
EMAIL_FROM=alerts@yourdomain.com
EMAIL_DEV_MODE=false

# Application
DEBUG=false
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]

# Monitoring
MONITOR_CHECK_INTERVAL=30        # seconds between checks
EMAIL_DEBOUNCE_MINUTES=60       # cooldown between alerts
```

### Docker Compose Configuration

The included `docker-compose.yml` provides a complete development environment:
- PostgreSQL database with health checks
- Redis for caching and pub/sub
- Application container with proper dependencies
- Volume persistence for data
- Health check endpoints

## 🔧 API Usage

### Authentication

```python
# Register a new user
POST /auth/register
{
  "email": "user@example.com",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Doe"
}

# Login
POST /auth/login
{
  "username": "user@example.com",
  "password": "secure_password"
}
```

### Monitor Management

```python
# Create a monitor
POST /api/v1/monitors
{
  "url": "https://example.com",
  "name": "My Website",
  "interval": 300
}

# Get all monitors
GET /api/v1/monitors

# Manual check
POST /api/v1/monitors/{monitor_id}/check
```

### Real-time Updates

```javascript
// Connect to monitor-specific WebSocket
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/${monitor_id}`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Status update:', data);
};

// Dashboard-wide updates
const dashboardWs = new WebSocket('ws://localhost:8000/api/v1/ws/dashboard');
```

## 🏗️ Architecture

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   PostgreSQL    │
│   WebSocket     │◄──►│   Backend       │◄──►│   Database      │
│   Client        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        
                              ▼                        
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Redis         │    │   Email         │
                       │   Pub/Sub       │    │   Service       │
                       │                 │    │   (Postmark)    │
                       └─────────────────┘    └─────────────────┘
```

### Key Components

- **Monitor Worker** - Background task that continuously checks endpoints
- **WebSocket Manager** - Handles real-time connections and broadcasting
- **Uptime Service** - Core monitoring logic and status management
- **Email Service** - Alert notifications with smart debouncing
- **Authentication System** - JWT-based user management

### Database Schema

```sql
-- Users table (FastAPI Users)
users: id, email, hashed_password, first_name, last_name, is_active

-- Monitors table
monitors: id, url, name, interval, status, last_latency_ms, 
         last_checked_at, last_alert_sent_at, user_id, is_active
```

## 📚 API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔄 Development Workflow

### Setting up Pre-commit Hooks
```bash
pre-commit install
```

### Code Quality
```bash
# Format code
black app/

# Lint code
ruff check app/

# Type checking
mypy app/
```

### Database Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🚀 Deployment

### Production Considerations

1. **Environment Security**
   - Use strong, unique SECRET_KEY
   - Enable SSL/TLS certificates
   - Configure proper CORS origins
   - Set EMAIL_DEV_MODE=false

2. **Database Optimization**
   - Set up connection pooling
   - Configure proper indexes
   - Regular backup strategy
   - Monitor query performance

3. **Monitoring & Logging**
   - Configure structured logging
   - Set up application monitoring
   - Health check endpoints
   - Error tracking integration

4. **Scalability**
   - Load balancer configuration
   - Redis cluster for high availability
   - Database read replicas
   - Horizontal pod autoscaling

### Docker Production Build
```dockerfile
# Use multi-stage build for smaller images
FROM python:3.12-slim as builder
# ... build steps

FROM python:3.12-slim
# ... production configuration
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation for new features
- Use conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The MIT License is a permissive license that allows for reuse within proprietary software provided all copies include the original copyright and license notice.

## 🙏 Acknowledgments

- **FastAPI** - For the excellent web framework
- **SQLModel** - For bridging SQLAlchemy and Pydantic
- **FastAPI Users** - For authentication management
- **Postmark** - For reliable email delivery

---

**Built with ❤️ using FastAPI and modern Python**