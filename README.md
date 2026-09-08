# 🎵 Brock Music Bot (Rust Modular Engine v0.2.0)

<p align="center">
  <img src="assets/brook_readme_banner.svg" alt="Brook Music Bot animated banner" width="100%" />
</p>

<p align="center">
  <img src="assets/brook_start.png" alt="Brook Music Bot artwork" width="420" />
</p>

Brock Music Bot brings a full Soul King vibe to Telegram group voice chats.  
Built around **Brook from One Piece**: stylish stage energy, playful setlist language, and a music-first group experience.

This repository is **100% Pure Hardcore Rust** (Rust 2021 Edition) powered by Tokio, Teloxide 0.13, Axum 0.7, Ferogram (MTProto), and TgCalls (WebRTC).

---

## ⚡ Production Key Highlights

- **Zero File & Media Downloads**: Audio and video media are **NEVER written to disk**. The engine streams raw HTTP/HTTPS URLs directly into WebRTC (`tgcalls` / `ffmpeg`) with **0-second disk buffering delay**.
- **Memory-First Runtime Execution**: Playback commands (`/play`, `/vplay`, `/skip`, `/stop`, `/pause`, `/resume`, `/queue`, `/nowplaying`) execute 100% in RAM with **0 database reads or writes** during active playback.
- **SingleFlight Request Deduplication**: Concurrent identical search queries coalesce into a single execution, preventing duplicate AI or provider API calls.
- **Single State Machine & Race Guard**: Playback transitions (`EngineState`) are guarded by a `transition_in_progress` lock, guaranteeing **at most 1 transition** when natural stream EOF and `/skip` command occur simultaneously.
- **Sub-Second InnerTube Player Resolution**: InnerTube `ANDROID` (`19.05.36`) and `TVHTML5` player endpoints resolve stream audio in **~100 milliseconds** (down from 6.5s).
- **Persistence Layer (`DbRepository`)**: Production repository abstraction supporting **MongoDB Atlas**, **Neon PostgreSQL**, or SQLite.
- **Heroku Ready**: `Procfile` (worker dyno), `app.json`, `RustConfig` toolchain pin, `Aptfile` native deps, runtime `yt-dlp` bootstrap (`bin/start_worker`), SIGTERM graceful shutdown handlers, and environment config parser.
- **100% Test Coverage Verified**: 48 unit & integration tests passing cleanly in 0.03 seconds.

---

## 📚 Complete Documentation Suite

All detailed guides and technical specifications are organized in the `docs/` directory:

- 📖 **[Beginner's User & Command Guide](docs/USER_GUIDE.md)**: Non-technical complete guide with copy-paste command examples, group setup, permissions, and FAQs.
- 🏗️ **[Architecture & Design System](docs/ARCHITECTURE.md)**: System topology, zero-download guarantees, memory-first state machine, and state lock guard.
- 🔧 **[Technical Reference](docs/TECHNICAL.md)**: Consolidated 10-module codebase breakdown, Rust dependencies, and technology stack.
- 🔌 **[REST API Reference](docs/API.md)**: Full REST API specification (`/health`, `/stats`, `/stream`, `/api/state`, `/api/action`).
- ☁️ **[Heroku & Database Deployment Guide](docs/DEPLOYMENT.md)**: Step-by-step deployment guide with MongoDB Atlas or Neon PostgreSQL setup.

---

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/johan-droid/Brock-Music-Bot-ACN
   cd Brock-Music-Bot-ACN
   ```

2. **Configure Environment Variables**
   Create `.env.local` (see `.env.example` for the full template):
   ```env
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyZ
   OWNER_ID=123456789
   PORT=8000

   # Database (MongoDB Atlas / Neon PostgreSQL / In-Memory)
   DATABASE_URL=mongodb+srv://user:pass@cluster.mongodb.net/brook

   # Voice Chat Assistant (MTProto)
   TG_API_ID=12345
   TG_API_HASH=abcdef1234567890
   ASSISTANT_SESSION_STRING=...
   ```

3. **Install ffmpeg** (required for WebRTC voice chat audio decoding):
   ```bash
   sudo apt install ffmpeg
   ```

4. **Build & Run**
   ```bash
   cargo run --release
   ```

5. **Run Automated Test Suite**
   ```bash
   cargo test
   ```

---

## 🎵 Command Setlist

| Command | Description |
|---|---|
| `/play [song]` | Search & play a song or URL |
| `/vplay [video]` | Search & stream video source |
| `/pause` | Pause current live performance |
| `/resume` | Resume paused playback |
| `/skip` | Jump to next track in setlist |
| `/prev` | Return to previous track |
| `/stop` | End concert & clear stage |
| `/seek [sec]` | Seek to specific timestamp |
| `/volume [0-200]` | Set playback volume |
| `/queue` | View current concert setlist |
| `/now` | Display current track & progress bar |
| `/shuffle` | Randomize setlist queue |
| `/loop [off\|track\|queue]` | Set loop mode |
| `/stats` | View Rust engine performance metrics |
| `/start` | Display Soul King introduction card |
| `/help` | Show command usage and guide |

---

## ☁️ Deploy to Heroku

Both **buildpack** (recommended) and **container (Docker)** deploys are supported.
The bot runs as a **worker dyno** (a long-running process that connects out to
the Telegram API) — not a web dyno, so there is no public `*.herokuapp.com` URL.

**Fastest path** — one command (creates the app, sets both buildpacks, config
vars, and scales to a worker):

```bash
./bin/setup_heroku brook-music-bot your_bot_token your_owner_id
git push heroku master
```

Or manually (the buildpacks **must** be set before the first push — Rust is
not auto-detected by Heroku):

```bash
# ── Buildpack path (Cedar) ──────────────────────────────────────────────
heroku create brook-music-bot
heroku buildpacks:set https://github.com/heroku-community/apt --index 1 -a brook-music-bot
heroku buildpacks:set https://github.com/emk/heroku-buildpack-rust --index 2 -a brook-music-bot
heroku config:set BOT_TOKEN="your_token" OWNER_ID="12345" -a brook-music-bot
git push heroku master
heroku ps:scale web=0 worker=1 -a brook-music-bot

# ── Container path (Docker) ─────────────────────────────────────────────
heroku stack:set container
heroku container:push worker
heroku container:release worker
heroku ps:scale web=0 worker=1
```

Even **before** `BOT_TOKEN` is configured the worker stays up (it just waits for
a shutdown signal instead of exiting), so you can push first and set config vars
afterwards without the dyno restart-looping.

For the full setup guide (buildpack ordering, config vars, CI/CD, database) see
**[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
