# 🎵 Brook Music Bot (Pure Hardcore Rust Crate)

<p align="center">
  <img src="assets/brook_readme_banner.svg" alt="Brook Music Bot animated banner" width="100%" />
</p>

<p align="center">
  <img src="assets/brook_start.png" alt="Brook Music Bot artwork" width="420" />
</p>

Brook Music Bot brings a full Soul King vibe to Telegram group chats.  
Built around **Brook from One Piece**: stylish stage energy, playful setlist language, and a music-first group experience.

This repository is **100% Pure Hardcore Rust** powered by Tokio, Teloxide, and Axum. Music resolution is built in: YouTube (native InnerTube search, optional yt-dlp for audio), Spotify & Apple Music (official metadata APIs with YouTube audio fallback + native preview snippets), SoundCloud, and direct audio links — **no mandatory external runtime, no Python, no IP bans**.

---

## ⚡ Key Highlights

- **100% Pure Hardcore Rust Crate**: Single high-performance compiled binary with zero Python dependencies.
- **Ultra-Low Resource Footprint**: Single compiled binary, no GIL. ~25 MB RAM in message-only mode; voice-chat mode additionally spawns one `ffmpeg` process per active voice chat.
- **Modular Layered Architecture**: Domain Core, Abstraction Ports, Application Services, Infrastructure Adapters, and Background Tokio Workers.
- **Teloxide Bot Dispatcher**: Type-safe command routing, callback query handling, and inline UI keyboard controls.
- **Multi-Platform Resolver**: Unified `TrackResolver` facade routing to per-platform `SourceAdapter`s — YouTube, Spotify, Apple Music, SoundCloud, and Direct Links.
- **IP-Ban Safe by Design**: Invidious/Piped instance rotation with health-skip, in-memory TTL result caching, official rate-limited APIs where possible, and native HEAD validation for direct URLs.
- **Axum HTTP REST Server**: Exposes `/health`, `/metrics`, `/metrics/prometheus`, and HTTP Basic Auth protected `/admin/*` REST API.
- **Real Voice-Chat Streaming**: `ferogram` (MTProto) + `tgcalls` (NTgCalls) stream actual audio into group voice chats via a dedicated assistant account — not just now-playing cards.
- **Heroku Ready**: Rust buildpack (or included `Dockerfile`), `Procfile`, `app.json`, apt-installed `ffmpeg`, no persistent disk requirements.

---

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/johan-droid/Brock-Music-Bot-ACN
   cd Brock-Music-Bot-ACN
   ```

2. **Configure Environment Variables**
   Create `.env.local` (see `.env.example` for the full list):
   ```env
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyZ
   OWNER_ID=123456789
   PORT=8000
   ADMIN_PASSWORD=supersecret

   # Streaming platforms (all optional; YouTube works out of the box)
   INVIDIOUS_INSTANCES=invidious.nerdvpn.de,vid.puffyan.us
   PIPED_INSTANCES=pipedapi.kavin.rocks,pipedapi.tokhmi.xyz
   SPOTIFY_CLIENT_ID=...
   SPOTIFY_CLIENT_SECRET=...
   SOUNDCLOUD_CLIENT_ID=...

   # Voice chat streaming (optional; see "Voice chat streaming setup" below)
   TG_API_ID=...
   TG_API_HASH=...
   ASSISTANT_SESSION_STRING=...
   ```

3. **Install ffmpeg** (required for voice-chat streaming): `sudo apt install ffmpeg`

4. **Build & Run (Pure Rust Crate)**
   ```bash
   cargo run --release
   ```
   Run once with `--export-session` on first voice setup to authenticate the assistant account and print `ASSISTANT_SESSION_STRING`.

---

## 🔧 Environment Variables

All configuration is via environment variables (loaded from `.env.local` / `.env` / Heroku config vars). See `.env.example` for a template.

| Variable | Default | Purpose |
|---|---|---|
| `BOT_TOKEN` | — | Telegram bot token from @BotFather (**required**) |
| `OWNER_ID` | — | Owner's numeric Telegram user ID (`/addsudo`, admin API) |
| `ADMIN_PASSWORD` | — | Password for the `/admin` HTTP dashboard (Basic auth) |
| `PORT` | — | Port for the Axum REST/health server (Heroku sets this) |
| `METRICS_HTTP_ENABLED` | `false` | Expose the `/metrics` endpoint |
| `METRICS_HTTP_TOKEN` | — | Bearer token protecting `/metrics` |
| `METRICS_PROMETHEUS_ENABLED` | `false` | Expose `/metrics/prometheus` |
| `INVIDIOUS_INSTANCES` | 5 public hosts | Comma-separated YouTube instances (rotated) |
| `PIPED_INSTANCES` | 4 public hosts | Comma-separated YouTube fallback instances |
| `YOUTUBE_ENABLED` | `true` | Set `false` to disable YouTube search |
| `YT_DLP_ENABLED` | `true` | Use the `yt-dlp` subprocess for YouTube audio (auto-skipped if the binary is missing) |
| `YT_DLP_BINARY` | `yt-dlp` | Path/name of the yt-dlp binary |
| `YT_DLP_TIMEOUT_SECS` | `20` | Max seconds allowed for a yt-dlp extraction attempt |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | — | Spotify Web API creds (enables Spotify) |
| `SOUNDCLOUD_CLIENT_ID` | — | SoundCloud `client_id` (enables SoundCloud) |
| `RESOLVER_CACHE_TTL_SECS` | `300` | In-memory search cache TTL (lower upstream traffic) |
| `RESOLVER_STREAM_CACHE_TTL_SECS` | `3600` | TTL for cached resolved stream URLs (repeat plays skip re-resolution) |
| `MAX_DIRECT_STREAM_MB` | `100` | Max size for direct audio streams |
| `ALLOWED_DIRECT_HOSTS` | (empty) | Allowlist of redirect hosts for direct links |
| `MAX_CONCURRENT_RESOLUTIONS` | `4` | Cap on simultaneous upstream track lookups |
| `MAX_QUEUE_SIZE` | `100` | Max tracks per chat queue |
| `DEFAULT_VOLUME` | `100` | Default playback volume |
| `COMMAND_COOLDOWN` | `3` | Seconds between commands per user |
| `TG_API_ID` / `TG_API_HASH` | — | Telegram API credentials (voice streaming) |
| `ASSISTANT_SESSION` | `assistant.session` | Local session file path for the assistant account |
| `ASSISTANT_SESSION_STRING` | — | Session string for the assistant (Heroku) |
| `MUSIC_MICROSERVICE_URL` | — | Legacy optional microservice (unused by built-in resolvers) |

---

## ☁️ Deploy to Heroku

The app is Heroku-ready. Platform resolution is pure HTTP by default (optional `yt-dlp` subprocess for YouTube audio), and voice-chat streaming uses `ferogram` + `tgcalls` over MTProto.

> **Voice chat streaming requires two things Heroku must provide: an `ffmpeg` binary and the assistant session string.** See [🔊 Voice chat streaming setup](#-voice-chat-streaming-setup) below.

### Option A — Deploy via GitHub (button)
Push this repo to GitHub, then create a new app from the Heroku Dashboard → **Deploy → GitHub**, or use the **Deploy to Heroku** button from `app.json`.

### Option B — Deploy via CLI
```bash
heroku create brook-music-bot
heroku buildpacks:add heroku-community/apt
heroku buildpacks:add https://github.com/emk/heroku-buildpack-rust
git push heroku main
```
The `heroku-community/apt` buildpack installs `ffmpeg`/`ffprobe` from the repo's `Aptfile` (required by `tgcalls` for audio decoding). Alternatively, deploy the included `Dockerfile` via Heroku Container Registry — it already bundles ffmpeg.

### 🔊 Voice chat streaming setup
The Telegram Bot API **cannot** stream audio into voice chats (`phone.joinGroupCall` is user-only). Real playback uses a dedicated **assistant user account** over MTProto:

1. Create a dedicated Telegram account (do not use one a human listens with — Telegram allows one voice-chat connection per account).
2. Get `API_ID` / `API_HASH` from https://my.telegram.org/api.
3. Add the assistant account to the group(s) where it should play (and ensure it has permission to speak, or is an admin).
4. Generate the session string **once** on a machine with a terminal (TTY):
   ```bash
   TG_API_ID=12345 TG_API_HASH=abcdef ./target/release/brook-music-bot --export-session
   # enter the assistant's phone number, the login code, and 2FA password if enabled
   # → prints: ASSISTANT_SESSION_STRING=<long secret string>
   ```
5. Configure:
   ```bash
   heroku config:set TG_API_ID=12345 TG_API_HASH=abcdef ASSISTANT_SESSION_STRING=<secret>
   ```

Without these, the bot falls back to **message-only** mode: it shows the now-playing card but cannot stream audio into the voice chat.

### Required config vars
```bash
heroku config:set BOT_TOKEN=123456789:ABC... OWNER_ID=123456789
```

### Optional config vars
```bash
# Rotate more public instances for better YouTube reliability
heroku config:set INVIDIOUS_INSTANCES=invidious.nerdvpn.de,vid.puffyan.us,inv.nadeko.net,iv.ggtyler.dev
heroku config:set PIPED_INSTANCES=pipedapi.kavin.rocks,pipedapi.tokhmi.xyz,piped-api.garudalinux.org

# Enable Spotify / SoundCloud
heroku config:set SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=...
heroku config:set SOUNDCLOUD_CLIENT_ID=...
```

> **Note:** `web` dyno type is used so Heroku's router health-checks `/health`. The single dyno serves both the REST API (on `$PORT`) and the Telegram bot.

### Why "no Python/yt-dlp by default"?
The old design *required* shelling out to a `yt-dlp` binary and used file-based sessions — both fragile on an ephemeral dyno. The Rust resolver is pure HTTP by default and only uses an optional `yt-dlp` subprocess to unlock YouTube audio when the InnerTube player endpoint is bot-guarded:
- **YouTube search** → native InnerTube web API (no key, no instances). Invidious `/api/v1` + Piped `/api/v1` are probed concurrently as a fallback (3s per-host timeout, dead hosts skipped instantly).
- **YouTube audio** → InnerTube player → optional `yt-dlp` (PO-token aware, best from datacenter IPs) → instance redirects, in that order.
- **Spotify / Apple Music** → official metadata APIs (client-credentials OAuth for Spotify; free iTunes Search API for Apple), audio via YouTube; Apple falls back to its native 30s preview snippet when YouTube is unavailable.
- **SoundCloud** → official `api-v2` search/resolve + progressive mp3 streams.
- **Direct links** → HTTP HEAD validation with range/content-type checks.

> The only external binaries the bot may use are **`ffmpeg`** (required by `tgcalls`, install via the `heroku-community/apt` buildpack or the included `Dockerfile`) and **`yt-dlp`** (optional — set `YT_DLP_ENABLED=false` to skip it entirely).

---

## 🎵 Supported Music Sources

| Source | Search | Links/URLs | Audio |
|---|---|---|---|
| YouTube | ✅ InnerTube (+ Invidious/Piped fallback) | ✅ | Direct stream (InnerTube / yt-dlp / instances) |
| Spotify | ✅ Web API | ✅ `open.spotify.com` / `spotify:track:` | Via YouTube, Apple preview |
| Apple Music | ✅ iTunes Search API | ✅ `music.apple.com` | Via YouTube, native preview |
| SoundCloud | ✅ api-v2 | ✅ `soundcloud.com` | Direct mp3 stream |
| Direct Links | ✅ HEAD validation | ✅ `.mp3/.ogg/.m4a/...` | Direct |

## 🎵 Command Setlist

| Command | Description |
|---|---|
| `/play [song]` | Search & play a song or URL |
| `/pause` | Pause current live performance |
| `/resume` | Resume paused playback |
| `/skip` | Jump to next track in setlist |
| `/prev` | Return to previous track |
| `/replay` | Restart current track |
| `/stop` | End concert & clear stage |
| `/seek [sec]` | Seek to specific timestamp |
| `/volume [0-200]` | Set playback volume |
| `/queue` | View current concert setlist |
| `/now` | Display current track & progress bar |
| `/shuffle` | Randomize setlist queue |
| `/loop [off\|track\|queue]` | Set loop mode |
| `/stats` | View Rust engine performance metrics |
| `/addsudo [id]` | Promote user to Sudo Commander (Owner) |
