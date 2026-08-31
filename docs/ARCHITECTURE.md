# Brock Music Bot — Architecture & System Design

## 1. High-Level System Architecture

```
                    ┌──────────────────┐
                    │     Telegram     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Command Layer   │  (/play, /vplay, /skip, /stop, /queue)
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   AI Receiver    │  (Human intent interpretation)
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Intelligent      │  (Provider health scoring & deduplication)
                    │ Router           │
                    └────────┬─────────┘
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
              YouTube    SoundCloud   Spotify
                 │           │           │
                 └───────────┼───────────┘
                             ▼
                    ┌──────────────────┐
                    │  Media Engine    │  (Memory-first queue & WebRTC stream)
                    └───────┬──────────┘
                            │
                            ▼
                     Assistant Account
                            │
                            ▼
                        Telegram VC (🔊 / 🎥)


       ┌──────────────────────────────────┐
       │       Persistence Layer          │
       │ MongoDB Atlas OR Neon PostgreSQL  │
       └──────────────────────────────────┘
```

## 2. Core Architectural Guarantees

1. **Zero File & Media Downloads**:
   - Audio and video files are **NEVER downloaded to disk**.
   - No `/tmp/brock-*` files, no `curl` commands, and zero disk I/O.
   - Raw stream URLs (`https://...`) are fed directly into WebRTC (`tgcalls`) for **0-second buffering delay**.

2. **Memory-First Runtime State**:
   - Playback state and queues execute 100% in RAM with **0 database reads or writes** during active playback commands (`/play`, `/skip`, `/stop`, `/pause`, `/resume`).

3. **SingleFlight Request Deduplication**:
   - Concurrent identical search queries coalesce into a single execution, saving external API quota.

4. **Single State Machine & Transition Lock**:
   - `EngineState` (`Idle`, `Queued`, `Playing`, `Paused`, `Stopping`, `Skipping`, `Finished`, `Error`) guarded by `transition_in_progress` lock to eliminate race conditions between natural stream EOF and `/skip` commands.
