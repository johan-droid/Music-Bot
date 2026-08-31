# Brock Music Bot — Heroku & Database Deployment Guide

This guide covers deploying Brock Music Bot to **Heroku** with **MongoDB Atlas** or **Neon PostgreSQL**.

## Deployment Requirements

- **Heroku CLI** installed
- Heroku App created (`heroku create <app-name>`)
- Rust Cargo Buildpack enabled

## Configuration Setup

Set environment variables on Heroku:

```bash
# Telegram Credentials
heroku config:set BOT_TOKEN="your_bot_token"
heroku config:set TG_API_ID="your_api_id"
heroku config:set TG_API_HASH="your_api_hash"
heroku config:set ASSISTANT_SESSION_STRING="your_session_string"

# AI & Database Configuration
heroku config:set NVIDIA_NIM_API_KEY="your_nvidia_api_key"
heroku config:set DATABASE_URL="mongodb+srv://user:pass@cluster.mongodb.net/brook"
```

## Deploying to Heroku

```bash
git push heroku main
```

The app will compile using Cargo and launch via `Procfile` (`web: target/release/brook-music-bot`).
