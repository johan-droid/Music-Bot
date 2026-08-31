# Brock Music Bot — REST API Documentation

The bot exposes lightweight HTTP REST endpoints via Axum on `PORT` (default: 8000) for health monitoring and metrics.

## Endpoints

### 1. GET `/health`
Returns system health and version status.

**Response**:
```json
{
  "status": "healthy",
  "version": "v0.2.0"
}
```

### 2. GET `/stats`
Returns active voice chat sessions and memory queue statistics.

**Response**:
```json
{
  "active_chats_count": 1,
  "status": "active"
}
```
