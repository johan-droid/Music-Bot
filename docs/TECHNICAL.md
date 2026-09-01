# Brock Music Bot — Technical Reference

## 1. Modular Codebase Layout (10 Core Modules)

```
src/
├── main.rs         - Entry point, Axum HTTP server, Teloxide dispatcher, SIGTERM handler
├── config.rs       - Environment configuration (Config), tracing logger, instance health checks
├── error.rs        - Unified BotError enum & Result<T> alias
├── ai.rs           - Intelligence Layer 1: AiReceiver (NVIDIA NIM LLM intent interpretation & local rule fallback)
├── router.rs       - Intelligence Layer 2: MusicRouter, SingleFlight request deduplication, provider health scoring
├── providers.rs    - Adapters for YouTube (InnerTube ANDROID/TVHTML5), SoundCloud, Spotify, Apple, Direct links
├── media_engine.rs - MediaEngine, ChatQueueState, EngineState machine, Direct WebRTC PlaybackTransport
├── db.rs           - DbRepository trait (MemoryFirstDbRepository for MongoDB Atlas / Neon PostgreSQL)
├── commands.rs     - Telegram bot commands (/play, /vplay, /skip, /stop, /queue, /pause, /resume, UI formatters)
└── tests.rs        - 48 automated unit & integration test cases
```

## 2. Technology Stack & Dependencies

- **Language & Runtime**: Rust 2021 Edition (Tokio async multi-threaded runtime)
- **Telegram Bot Framework**: Teloxide 0.13
- **MTProto & WebRTC Transport**: Ferogram 0.6.5 & TgCalls 0.2.0
- **HTTP REST API & Server**: Axum 0.7 & Reqwest 0.12 (rustls TLS)
- **State Management**: DashMap 5.5 (lock-free concurrent maps) & Tokio RwLock
- **Database Abstraction**: `DbRepository` (Memory-first MongoDB Atlas / Neon PostgreSQL adapter)
