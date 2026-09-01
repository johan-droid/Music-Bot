# Brock Music Bot — REST API Documentation

The bot exposes lightweight HTTP REST endpoints via Axum on `PORT` (default: 8000) for health monitoring, stream proxying, web control, and system metrics.

## Endpoints

### 1. GET `/`
Root status endpoint.

**Response**:
```json
{
  "service": "Brock Music Bot",
  "status": "online",
  "version": "v0.2.0"
}
```

### 2. GET `/health`
System health check.

**Response**:
```json
{
  "status": "healthy",
  "version": "v0.2.0"
}
```

### 3. GET `/static/brook.png`
Serves static Soul King artwork image (`image/png`) cached with HTTP headers `max-age=86400`.

### 4. GET `/stream?yt={video_id}`
Real-time piped HTTP audio stream proxy. Spawns `yt-dlp` subprocess and streams `audio/webm` stdout directly into WebRTC/`tgcalls` without writing temp files to disk.

### 5. GET `/api/state?chat_id={id}`
Returns real-time playback state (`position_secs`, `engine_state`, `voice_state`, `queue_len`, `volume`, `loop_mode`) for a given Telegram chat ID.

### 6. POST `/api/action`
Sends remote playback commands (`pause`, `resume`, `skip`, `stop`, `play`).

**Payload Example**:
```json
{
  "action": "play",
  "chat_id": -100123456789,
  "query": "Binks Sake"
}
```

### 7. GET `/stats`
Returns active voice chat sessions and registered platform adapters.

**Response**:
```json
{
  "status": "online",
  "active_chats": 1,
  "platforms": ["DirectUrl", "YouTube", "Spotify", "AppleMusic", "SoundCloud"]
}
```
