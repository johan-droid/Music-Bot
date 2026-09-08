# Heroku worker dyno: this is a long-running Telegram bot, NOT a web app.
# Workers get no HTTP routing and no $PORT — the bot connects out to the
# Telegram Bot API / MTProto / provider APIs.
# `target/release/brook-music-bot` is produced by the emk/heroku-buildpack-rust
# buildpack after `cargo build --release --locked`. `bin/start_worker` ensures
# the optional yt-dlp tool is present at runtime, then execs the Rust binary
# (SIGTERM still reaches the bot directly).
worker: ./bin/start_worker
