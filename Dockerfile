# syntax=docker/dockerfile:1
# Heroku container deployment for Brook Music Bot
# Builds a minimal runtime image with Rust binary + ffmpeg for audio processing

# ---- Builder stage ----
FROM rust:1.85-bookworm AS builder

# Install system dependencies for native crates (opus, openssl, etc.) and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    cmake \
    pkg-config \
    libssl-dev \
    libopus-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependencies: copy manifests first
COPY Cargo.toml Cargo.lock ./
# Create dummy source to build dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release --locked
# Remove dummy and copy real source
RUN rm -rf src
COPY src ./src
# Build actual binary
RUN cargo build --release --locked

# ---- Runtime stage ----
FROM debian:bookworm-slim

# Runtime dependencies: ca-certificates for HTTPS, ffmpeg for audio decoding,
# libopus0 and libssl3 for native crates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    ffmpeg \
    libopus0 \
    libssl3 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp (standalone binary) for YouTube audio extraction
RUN pip3 install --break-system-packages --no-cache-dir yt-dlp \
    && ln -sf /usr/local/bin/yt-dlp /usr/bin/yt-dlp \
    && yt-dlp --version

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/brook-music-bot /app/brook-music-bot



# Non-root user for security
RUN useradd -r -u 1001 -s /sbin/nologin appuser && chown -R appuser:appuser /app
USER appuser

# Heroku sets PORT env; the binary binds to $PORT for the Axum health API
ENV RUST_LOG=info
EXPOSE 8000

CMD ["/app/brook-music-bot"]