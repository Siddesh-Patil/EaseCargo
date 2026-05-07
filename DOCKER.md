# 🐳 EaseCargo Docker Setup Guide

## Overview

EaseCargo runs via Docker Compose for easy local development and deployment. The project uses a single-service setup with persistent database storage.

## Prerequisites

- **Docker Desktop** - [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Docker Compose** (v2.0+) - Usually included with Docker Desktop

## Quick Start

Navigate to the project directory and run:

```bash
docker-compose up
```

The application will be available at **`http://localhost:5000`**

### Common Docker Compose Commands

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# View logs from specific service
docker-compose logs -f easecargo

# Stop the application
docker-compose down

# Stop and remove all volumes (⚠️ deletes data)
docker-compose down -v

# Rebuild the image
docker-compose up -d --build

# Run a command in the container
docker-compose exec easecargo bash

# Check service status
docker-compose ps
```

## Environment Configuration

Create a `.env` file in the project root to override default environment variables:

```bash
cp .env.example .env
```

Edit `.env` as needed:

```env
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
APP_PORT=5000
DATABASE_URL=sqlite:////app/instance/easecargo.db
```

Then restart:

```bash
docker-compose up -d
```

## Database

### Persistence

The database is stored in a named volume (`easecargo-db`) which persists data between container restarts:

```bash
# View volumes
docker volume ls | grep easecargo

# Inspect volume details
docker volume inspect easecargo_easecargo-db

# Remove volume (⚠️ DELETES DATA)
docker volume rm easecargo_easecargo-db
```

### Database Locking

On first initialization, the database is locked to read-only mode to prevent accidental modifications. If you need to modify the database:

```bash
# Unlock the database within the container
docker-compose exec easecargo chmod 644 instance/easecargo.db

# Lock it again
docker-compose exec easecargo chmod 444 instance/easecargo.db
```

## Development vs Production

### Development Mode

For hot-code reloading during development:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This mounts your source code as a volume and runs Flask in debug mode.

### Production Mode (Default)

The default `docker-compose.yml` runs Gunicorn with 4 workers, suitable for production deployments.

## Health Checks

The container includes health checks that automatically restart if the application becomes unhealthy:

```bash
# Check container health
docker-compose ps

# Monitor health check logs
docker inspect easecargo-app --format='{{json .State.Health}}' | jq .
```

## Troubleshooting

### Container won't start

```bash
# View full logs
docker-compose logs easecargo

# Check if port is in use
netstat -ano | findstr :5000  # Windows
lsof -i :5000                  # Linux/macOS
```

### Port 5000 already in use

Change the port in docker-compose.yml:

```yaml
ports:
  - "5001:5000"  # Use port 5001 instead
```

### Database errors

```bash
# Reset database (removes data)
docker-compose down -v
docker-compose up -d
```

### Permission issues

```bash
# Grant write permission if needed
docker-compose exec easecargo chmod 644 instance/easecargo.db
```

## Volume Management

### Bind Mounts (Development)

During development, these directories are directly mounted from your host machine:

- `./static/` → `/app/static` (HTML/CSS/JS files)
- `./data/` → `/app/data` (shipment CSV and coordinates)

### Named Volumes (Data Persistence)

- `easecargo-db` → `/app/instance` (SQLite database)

## Docker Compose Configuration

The `docker-compose.yml` file includes:

| Setting | Details |
|---------|---------|
| **Image** | Built from local Dockerfile |
| **Port** | 5000 (configurable via APP_PORT) |
| **Volumes** | easecargo-db, static/, data/ |
| **Health Check** | Every 30 seconds, 3 retries |
| **Restart** | Automatic on failure |
| **Logging** | JSON file driver, max 10MB per file |

## Performance

The default configuration runs:
- **Gunicorn**: 4 workers (sync mode)
- **Timeout**: 60 seconds per request
- **Memory**: ~500MB typical usage

To modify, edit the docker-entrypoint.sh:

```bash
# Change number of workers
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 8 \  # Increase from 4
    --worker-class sync \
    --timeout 60 \
    app:app
```

## Next Steps

1. **Verify it's running**: Visit `http://localhost:5000`
2. **Check the logs**: `docker-compose logs -f`
3. **Explore the app**: Navigate through discover, dashboard, and tracking pages
4. **For development**: Use `-f docker-compose.dev.yml` for hot-reloading

## Additional Resources

- [Docker Documentation](https://docs.docker.com)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Gunicorn Documentation](https://gunicorn.org/)

---

**Happy coding with Docker! 🚀**
