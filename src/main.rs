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

use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;

use axum::routing::get;
use axum::{Json, Router};
use serde_json::json;
use teloxide::prelude::*;

use crate::ai::AiReceiver;
use crate::commands::{handle_command, BotCommand};
use crate::config::{init_logger, Config};
use crate::db::{DbRepository, MemoryFirstDbRepository};
use crate::media_engine::{connect_voice_transport, InMemoryQueueRepository, MediaEngine, PlaybackTransport, TelegramAudioTransport, VoiceChatTransport};
use crate::providers::{AppleResolver, DirectResolver, SoundCloudResolver, SpotifyResolver, YouTubeResolver};
use crate::router::{MusicRouter, Platform, Route, SourceAdapter, UrlResolver, VideoResolver};

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

    // 4. Axum HTTP Server
    let port = config.port.unwrap_or(8000);
    let app_state_api = state.clone();
    let app = Router::new()
        .route("/health", get(|| async { Json(json!({"status": "healthy", "version": "v0.2.0"})) }))
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
        }));

    tokio::spawn(async move {
        let addr = SocketAddr::from(([0, 0, 0, 0], port));
        let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
        axum::serve(listener, app).await.unwrap();
    });

    // 5. Teloxide Dispatcher
    if let Some(bot) = bot {
        let ai = state.ai.clone();
        let router = state.router.clone();
        let url_resolver = state.url_resolver.clone();
        let video_resolver = state.video_resolver.clone();
        let media_engine = state.media_engine.clone();

        let handler = Update::filter_message().filter_command::<BotCommand>().endpoint(
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