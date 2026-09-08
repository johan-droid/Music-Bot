# Brock Music Bot — Heroku Deployment Guide

This guide covers deploying Brock Music Bot to **Heroku**, both via the classic
**buildpack (Cedar)** path (recommended) and the **container (Docker)** path.

---

## 1. Buildpack deployment (recommended)

The repo ships everything the buildpacks need:

| File | Purpose |
|---|---|
| `Procfile` | Runs the bot as a Heroku **worker** dyno via `bin/start_worker`, which guarantees the optional `yt-dlp` tool at runtime and then `exec`s `target/release/brook-music-bot` |
| `RustConfig` | Pins the Rust toolchain for the [emk Rust buildpack](https://github.com/emk/heroku-buildpack-rust) to the exact version the code is verified against (`VERSION=1.97.1`, `--release --locked`). Local `cargo` ignores this file. |
| `Aptfile` | Native build deps (`clang`, `cmake`, `pkg-config`, `libssl-dev`, `libopus-dev`) and runtime deps (`ffmpeg`, `python3`, `python3-pip`) |
| `bin/start_worker` | Worker dyno entry point (see `Procfile`): installs `yt-dlp` into `/tmp` if missing, then `exec`s the compiled binary |
| `app.json` | App template for the **Deploy to Heroku** button (env vars + buildpacks) |

### Steps

**1. Create the app with both buildpacks — order matters (apt BEFORE Rust):**

```bash
heroku create brook-music-bot
heroku buildpacks:set https://github.com/heroku-community/apt --index 1 -a brook-music-bot
heroku buildpacks:set https://github.com/emk/heroku-buildpack-rust --index 2 -a brook-music-bot
```

> The apt buildpack installs the packages listed in `Aptfile` **before** the Rust
> buildpack runs `cargo build --release --locked`. The native headers (`libopus-dev`,
> `libssl-dev`, `clang`, `cmake`, `pkg-config`) are required to compile crates
> such as `tgcalls`, `ferogram` and `rustls`. The installed packages stay in the
> slug, so `ffmpeg` and `python3` are also available at runtime.

**2. Set config vars (at minimum `BOT_TOKEN`):**

```bash
heroku config:set BOT_TOKEN="123456789:your_token_here" -a brook-music-bot
heroku config:set OWNER_ID="123456789" -a brook-music-bot
# optional:
heroku config:set ADMIN_PASSWORD="..." -a brook-music-bot
heroku config:set TG_API_ID=... TG_API_HASH=... ASSISTANT_SESSION_STRING=... -a brook-music-bot
heroku config:set DATABASE_URL="mongodb+srv://..." -a brook-music-bot
```

Workers receive **no `$PORT`** (that variable is injected for web dynos only). The bot falls back to port `8000` for its internal HTTP API — harmless, since Heroku doesn't route HTTP to workers.

**3. Deploy (as a worker):**

```bash
git push heroku master          # or: git push heroku your-local-branch:master
heroku ps:scale web=0 worker=1 -a brook-music-bot
```

**4. Verify:**

```bash
heroku ps -a brook-music-bot        # "worker" should be "up" (web stays at 0)
heroku logs --tail -a brook-music-bot
```

> ⚠️ This app is a **worker dyno, not a web app**. There is no
> `https://brook-music-bot.herokuapp.com/health` URL — Heroku does not route
> HTTP traffic to workers. The bot connects **out** to the Telegram Bot API,
> MTProto, and the provider APIs, so it needs no inbound port. To poke at the
> internal Axum endpoint (e.g. `/api/state`), use `heroku run bash` /
> `heroku run ./target/release/brook-music-bot` and hit `localhost:8000`
> interactively.

> Even **before** `BOT_TOKEN` is set the worker stays up (it simply waits for a
> shutdown signal instead of exiting), so you can push first and set config vars
> afterwards without the dyno restart-looping. Once you add config vars, Heroku
> restarts the dyno with them.

### Troubleshooting

- **Rust toolchain:** pinned via the `RustConfig` file (`VERSION=1.97.1`) for the
  emk buildpack. Bump it only after verifying locally with
  `cargo build --release --locked`.
- **Native crates fail to compile:** you are missing the apt buildpack entries.
  Re-run the `buildpacks:set` steps above (with `--index 1` for apt) and redeploy.
- **yt-dlp missing:** `bin/start_worker` installs it into the dyno's writable
  `/tmp/ytdlp` on every boot (the slug is read-only at runtime). If the install
  fails (no network / no pip), the bot still runs and falls back to the built-in
  InnerTube / Invidious / Piped resolvers. You can also set `YT_DLP_ENABLED=false`.
- **Stack:** classic buildpacks run on Cedar stacks (`heroku-22` / `heroku-24`).
  If you hit buildpack trouble on a newer stack, `heroku stack:set heroku-22`
  (then redeploy) is a proven fallback.

---

## 2. Container deployment (Docker)

Prefer the `container` stack if you want the exact build from the committed
`Dockerfile`:

```bash
heroku create brook-music-bot-container
heroku stack:set container -a brook-music-bot-container
heroku config:set BOT_TOKEN="..." -a brook-music-bot-container
heroku container:push worker -a brook-music-bot-container
heroku container:release worker -a brook-music-bot-container
heroku ps:scale web=0 worker=1 -a brook-music-bot-container
```

The image is built with Rust `1.97` (see `RustConfig` for the exact channel),
bundles `ffmpeg`, `libopus`, `python3` and `yt-dlp`, and runs as a
non-root user. It runs as a **worker** process type — no HTTP routing, no `$PORT`.

---

## 3. CI/CD (GitHub Actions)

`.github/workflows/deploy.yml` validates and deploys automatically on push to
`master` or `main`:

1. `validate-and-build` installs the same native deps as the Heroku `Aptfile`,
   then runs `cargo check` + the test suite against Rust `1.97.1`.
2. `deploy` sets the two buildpacks and pushes the code to Heroku.

Add three repository secrets:

| Secret | Value |
|---|---|
| `HEROKU_API_KEY` | Your Heroku account API key (`heroku authorizations:create`) |
| `HEROKU_APP_NAME` | Your app name (e.g. `brook-music-bot`) |
| `HEROKU_EMAIL` | The account email that owns the API key |

---

## 4. Database (optional)

Set `DATABASE_URL` to a MongoDB Atlas or Neon PostgreSQL connection string to
enable the persistent `DbRepository`. Without it, the bot falls back to the
in-memory repository (queue state is not persisted across restarts).
