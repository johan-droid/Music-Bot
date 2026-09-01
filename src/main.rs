mod ai;
mod commands;
mod config;
mod db;
mod error;
mod media_engine;
mod providers;
mod router;

#[cfg(test)]
mod tests;

use std::collections::HashMap;
use std::net::SocketAddr;
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;

use axum::body::Body;
use axum::extract::Query;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::{Json, Router};
use serde_json::json;
use teloxide::prelude::*;
use tokio_util::io::ReaderStream;

use crate::ai::AiReceiver;
use crate::commands::{handle_command, BotCommand};
use crate::config::{init_logger, Config};
use crate::db::{DbRepository, MemoryFirstDbRepository};
use crate::media_engine::{connect_voice_transport, InMemoryQueueRepository, MediaEngine, PlaybackTransport, TelegramAudioTransport, VoiceChatTransport};
use crate::providers::{AppleResolver, DirectResolver, SoundCloudResolver, SpotifyResolver, YouTubeResolver};
use crate::router::{MusicRouter, Platform, Route, SourceAdapter, TrackResolver, UrlResolver, VideoResolver};

async fn stream_handler(Query(params): Query<HashMap<String, String>>) -> impl IntoResponse {
    let video_id = match params.get("yt") {
        Some(id) if !id.is_empty() => id.to_string(),
        _ => return (axum::http::StatusCode::BAD_REQUEST, "Missing yt param").into_response(),
    };

    let url = format!("https://www.youtube.com/watch?v={video_id}");
    tracing::info!(video_id = %video_id, "Piping yt-dlp real-time audio stream over HTTP");

    let child = match tokio::process::Command::new("yt-dlp")
        .args([
            "--no-warnings",
            "--no-playlist",
            "--format",
            "bestaudio[ext=m4a]/bestaudio",
            "-o",
            "-",
            &url,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
    {
        Ok(c) => c,
        Err(e) => {
            tracing::error!(error = %e, "Failed to spawn yt-dlp audio stream process");
            return (axum::http::StatusCode::INTERNAL_SERVER_ERROR, format!("Failed to spawn yt-dlp: {e}")).into_response();
        }
    };

    let stdout = match child.stdout {
        Some(s) => s,
        None => return (axum::http::StatusCode::INTERNAL_SERVER_ERROR, "Failed to capture stdout").into_response(),
    };

    let stream = ReaderStream::new(stdout);
    let body = Body::from_stream(stream);

    axum::response::Response::builder()
        .header("Content-Type", "audio/webm")
        .header("Cache-Control", "no-cache")
        .body(body)
        .unwrap()
}

use axum::extract::State;
use axum::routing::post;
use serde::Deserialize;
use crate::media_engine::{EngineState, LoopMode, PlaybackState, VoiceState};

async fn index_handler() -> Json<serde_json::Value> {
    Json(json!({"service": "Brock Music Bot", "status": "online", "version": "v0.2.0"}))
}

async fn brook_image_handler() -> impl IntoResponse {
    (
        [("Content-Type", "image/png"), ("Cache-Control", "public, max-age=86400")],
        include_bytes!("../assets/brook.png").as_slice(),
    )
}

async fn api_state_handler(
    State(app): State<Arc<AppState>>,
    Query(params): Query<HashMap<String, String>>,
) -> Json<serde_json::Value> {
    let chat_id = params.get("chat_id").and_then(|s| s.parse().ok()).unwrap_or(0);
    let pb = app.media_engine.state(chat_id).await.unwrap_or_else(|_| PlaybackState {
        current: None,
        position_secs: 0,
        is_paused: false,
        loop_mode: LoopMode::Off,
        volume: 100,
        queue_len: 0,
        history_len: 0,
        engine_state: EngineState::Idle,
        voice_state: VoiceState::Disconnected,
        playback_generation: 0,
        vc_generation: 0,
        owner_user_id: None,
        owner_user_name: String::new(),
        session_id: String::new(),
        last_error: None,
        player_message_id: None,
        queue: Vec::new(),
    });

    Json(json!({
        "current": pb.current,
        "position_secs": pb.position_secs,
        "is_paused": pb.is_paused,
        "loop_mode": pb.loop_mode.display_text(),
        "volume": pb.volume,
        "queue_len": pb.queue_len,
        "history_len": pb.history_len,
        "engine_state": pb.engine_state.display_text(),
        "voice_state": pb.voice_state.display_text(),
        "playback_generation": pb.playback_generation,
        "last_error": pb.last_error,
    }))
}

#[derive(Deserialize)]
struct ActionPayload {
    action: String,
    chat_id: Option<i64>,
    query: Option<String>,
}

async fn api_action_handler(
    State(app): State<Arc<AppState>>,
    Json(payload): Json<ActionPayload>,
) -> Json<serde_json::Value> {
    let chat_id = payload.chat_id.unwrap_or(0);
    match payload.action.as_str() {
        "pause" => { let _ = app.media_engine.pause(chat_id).await; }
        "resume" => { let _ = app.media_engine.resume(chat_id).await; }
        "skip" => { let _ = app.media_engine.skip(chat_id).await; }
        "stop" => { let _ = app.media_engine.stop(chat_id).await; }
        "play" => {
            if let Some(q) = payload.query.filter(|s| !s.trim().is_empty()) {
                let state_me = app.media_engine.clone();
                let router_me = app.router.clone();
                let ai_me = app.ai.clone();
                tokio::spawn(async move {
                    if let Ok(processed) = ai_me.process_query(&q).await {
                        if let Ok(t) = router_me.search(&processed, 0, "WebUser").await {
                            let _ = state_me.repo.enqueue(chat_id, t.clone()).await;
                            let _ = state_me.play(chat_id, &t).await;
                        }
                    }
                });
            }
        }
        _ => {}
    }
    Json(json!({"status": "ok"}))
}

pub struct AppState {
    pub config: Config,
    pub media_engine: Arc<MediaEngine>,
    pub ai: Arc<AiReceiver>,
    pub router: Arc<MusicRouter>,
    pub url_resolver: Arc<UrlResolver>,
    pub video_resolver: Arc<VideoResolver>,
    pub db: Arc<MemoryFirstDbRepository>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_logger();
    tracing::info!("☠️ Initializing Brook Music Bot (Rust Modular Engine v0.2.0)");

    let config = Config::load().await;
    let db_repo = Arc::new(MemoryFirstDbRepository::new(config.database_url.clone()));
    db_repo.log_analytics("bot_startup", "Heroku dyno initialized").await?;

    let http_client = reqwest::Client::builder()
        .timeout(Duration::from_secs(15))
        .connect_timeout(Duration::from_secs(5))
        .build()
        .unwrap_or_else(|_| reqwest::Client::new());

    // 1. Providers
    let youtube = Arc::new(YouTubeResolver::new(
        http_client.clone(),
        if config.active_invidious_instances.is_empty() {
            config.invidious_instances.clone()
        } else {
            config.active_invidious_instances.clone()
        },
        if config.active_piped_instances.is_empty() {
            config.piped_instances.clone()
        } else {
            config.active_piped_instances.clone()
        },
        config.resolver_cache_ttl_secs,
        config.yt_dlp_enabled,
        config.yt_dlp_binary.clone(),
        Duration::from_secs(config.yt_dlp_timeout_secs),
    ));

    let spotify = Arc::new(SpotifyResolver::new(
        http_client.clone(),
        config.spotify_client_id.clone(),
        config.spotify_client_secret.clone(),
        Some(youtube.clone()),
    ));

    let apple = Arc::new(AppleResolver::new(http_client.clone(), Some(youtube.clone())));
    let soundcloud = Arc::new(SoundCloudResolver::new(
        http_client.clone(),
        config.soundcloud_client_id.clone(),
        Some(youtube.clone()),
    ));
    let direct = Arc::new(DirectResolver::new(http_client, &config));

    let mut routes = vec![Route::new(Platform::DirectUrl, direct)];
    if config.youtube_enabled {
        routes.push(Route::new(Platform::YouTube, youtube.clone()));
    }
    if config.spotify_client_id.is_some() && config.spotify_client_secret.is_some() {
        routes.push(Route::new(Platform::Spotify, spotify.clone()));
    }
    routes.push(Route::new(Platform::AppleMusic, apple.clone()));
    if config.soundcloud_client_id.is_some() {
        routes.push(Route::new(Platform::SoundCloud, soundcloud.clone()));
    }

    let mut search_chain: Vec<Arc<dyn SourceAdapter>> = Vec::new();
    if config.youtube_enabled {
        search_chain.push(youtube.clone());
    }
    if config.spotify_client_id.is_some() && config.spotify_client_secret.is_some() {
        search_chain.push(spotify.clone());
    }
    search_chain.push(apple.clone());
    if config.soundcloud_client_id.is_some() {
        search_chain.push(soundcloud.clone());
    }

    // 2. Music Router, URL Resolver, Video Resolver & AI Receiver
    let router = Arc::new(MusicRouter::new(routes, search_chain, &config));
    let url_resolver = Arc::new(UrlResolver::new(router.clone()));
    let video_resolver = Arc::new(VideoResolver::new(router.clone()));
    let ai = Arc::new(AiReceiver::new(&config));

    // 3. Media Engine (Queue + Transport)
    let queue_repo = Arc::new(InMemoryQueueRepository::new(config.max_queue_size, config.default_volume));
    let bot = config.bot_token.as_ref().map(|t| Bot::new(t.clone()));

    let voice_transport: Option<Arc<VoiceChatTransport>> =
        connect_voice_transport(&config, bot.clone(), router.clone())
            .await
            .map(Arc::new);

    let transport: Arc<dyn PlaybackTransport> = match &voice_transport {
        Some(vt) => vt.clone(),
        None => Arc::new(TelegramAudioTransport::new(bot.clone())),
    };

    let media_engine = Arc::new(MediaEngine::new(queue_repo, transport));

    let state = Arc::new(AppState {
        config: config.clone(),
        media_engine,
        ai,
        router,
        url_resolver,
        video_resolver,
        db: db_repo.clone(),
    });

    // 4. Axum HTTP Server & Web UI
    let port = config.port.unwrap_or(8000);
    let app_state_api = state.clone();

    let app = Router::new()
        .route("/", get(index_handler))
        .route("/static/brook.png", get(brook_image_handler))
        .route("/health", get(|| async { Json(json!({"status": "healthy", "version": "v0.2.0"})) }))
        .route("/stream", get(stream_handler))
        .route("/api/state", get(api_state_handler))
        .route("/api/action", post(api_action_handler))
        .route("/stats", get(move || {
            let st = app_state_api.clone();
            async move {
                let chats = st.media_engine.repo.active_chats().len();
                Json(json!({
                    "status": "online",
                    "active_chats": chats,
                    "platforms": st.router.registered_platforms()
                }))
            }
        }))
        .with_state(state.clone());

    tokio::spawn(async move {
        let addr = SocketAddr::from(([0, 0, 0, 0], port));
        let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
        tracing::info!(port, "Soul King Brook Web UI live at http://0.0.0.0:{port}");
        axum::serve(listener, app).await.unwrap();
    });

    // 5a. 1-second Playback Ticker: Advances position_secs, triggers advance_to_next_track on EOF, and prunes idle sessions
    let me_playback_ticker = state.media_engine.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(1));
        let mut tick_counter: u64 = 0;
        loop {
            interval.tick().await;
            tick_counter += 1;
            if tick_counter.is_multiple_of(60) {
                me_playback_ticker.repo.prune_inactive_sessions(Duration::from_secs(1800));
            }
            let active_chats = me_playback_ticker.repo.active_chats();
            for chat_id in active_chats {
                if let Ok(st) = me_playback_ticker.state(chat_id).await {
                    if !st.is_paused && st.engine_state == crate::media_engine::EngineState::Playing && st.voice_state == crate::media_engine::VoiceState::Connected {
                        if let Ok(true) = me_playback_ticker.repo.tick_seconds(chat_id, 1).await {
                            tracing::info!(chat_id, "[TICKER] track reached EOF duration; advancing to next track");
                            let _ = me_playback_ticker.advance_to_next_track(chat_id, crate::media_engine::TransitionReason::Eof).await;
                        }
                    }
                }
            }
        }
    });

    // 5b. Background In-Group Telegram Progress Ticker
    if let Some(bot_ticker) = bot.clone() {
        let me_ticker = state.media_engine.clone();
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(5));
            loop {
                interval.tick().await;
                let active_chats = me_ticker.repo.active_chats();
                for chat_id in active_chats {
                    if let Ok(st) = me_ticker.state(chat_id).await {
                        if let (Some(msg_id), Some(curr)) = (st.player_message_id, &st.current) {
                            if !st.is_paused && st.engine_state == crate::media_engine::EngineState::Playing {
                                let text = crate::commands::SoulKingUI::format_now_playing(
                                    curr,
                                    st.position_secs,
                                    st.is_paused,
                                    &st.loop_mode,
                                    st.voice_state,
                                    &st.queue,
                                );
                                let keyboard = crate::commands::SoulKingUI::now_playing_keyboard(st.is_paused);
                                let _ = bot_ticker
                                    .edit_message_text(teloxide::types::ChatId(chat_id), teloxide::types::MessageId(msg_id), text)
                                    .parse_mode(teloxide::types::ParseMode::Html)
                                    .reply_markup(keyboard)
                                    .await;
                            }
                        }
                    }
                }
            }
        });
    }

    // 6. Teloxide Dispatcher (Commands + In-Group Callback Queries)
    if let Some(bot) = bot {
        let ai = state.ai.clone();
        let router = state.router.clone();
        let url_resolver = state.url_resolver.clone();
        let video_resolver = state.video_resolver.clone();
        let media_engine = state.media_engine.clone();
        let media_engine_cb = state.media_engine.clone();

        let handler = dptree::entry()
            .branch(
                Update::filter_message().filter_command::<BotCommand>().endpoint(
                    move |bot: Bot, msg: Message, cmd: BotCommand| {
                        let ai = ai.clone();
                        let router = router.clone();
                        let url_resolver = url_resolver.clone();
                        let video_resolver = video_resolver.clone();
                        let media_engine = media_engine.clone();
                        async move {
                            handle_command(bot, msg, cmd, ai, router, url_resolver, video_resolver, media_engine).await
                        }
                    },
                )
            )
            .branch(
                Update::filter_callback_query().endpoint(
                    move |bot: Bot, q: teloxide::types::CallbackQuery| {
                        let media_engine = media_engine_cb.clone();
                        async move {
                            crate::commands::handle_callback_query(bot, q, media_engine).await
                        }
                    },
                )
            )
            .branch(
                Update::filter_message().endpoint(|_bot: Bot, _msg: Message| async move {
                    Ok::<(), anyhow::Error>(())
                })
            );

        let mut dispatcher = Dispatcher::builder(bot, handler).build();
        tokio::select! {
            _ = dispatcher.dispatch() => {},
            _ = tokio::signal::ctrl_c() => {
                tracing::info!("Received shutdown signal, cleaning up streams...");
                if let Some(vt) = &voice_transport {
                    vt.shutdown_all().await;
                }
            }
        }
    }

    Ok(())
}