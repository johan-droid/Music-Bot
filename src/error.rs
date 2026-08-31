use thiserror::Error;

#[derive(Error, Debug)]
pub enum BotError {
    #[error("HTTP client error: {0}")]
    HttpClient(#[from] reqwest::Error),

    #[error("Telegram error: {0}")]
    Telegram(#[from] teloxide::RequestError),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Platform configuration error: {0}")]
    PlatformConfig(String),

    #[error("Rate limited by platform: {0}")]
    RateLimited(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

pub type Result<T> = std::result::Result<T, BotError>;
