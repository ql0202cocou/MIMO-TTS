use std::env;

pub const VERSION: &str = "0.2.0";

pub const SPEED_MIN: u8 = 5;
pub const SPEED_MAX: u8 = 50;
pub const SPEED_DEFAULT: u8 = 30;

pub const MIN_SEGMENT_LENGTH: usize = 50;
pub const MIN_COMMA_SEGMENT_LENGTH: usize = 20;

pub const CONTENT_TYPE_MAP: &[(&str, &str)] = &[
    ("wav", "audio/wav"),
    ("mp3", "audio/mpeg"),
    ("pcm16", "audio/L16"),
];

#[derive(Clone)]
pub struct Settings {
    pub api_base_url: String,
    pub api_key: String,
    pub username: String,
    pub password: String,
    pub model: String,
    pub default_voice: String,
    pub default_style: String,
    pub timeout_secs: u64,
    pub max_text_length: usize,
    pub output_format: String,
    pub rate_limit_per_minute: u32,
    pub max_request_size: usize,
    pub listen_addr: String,
    pub log_level: String,
}

impl Settings {
    pub fn from_env() -> Self {
        let _ = dotenvy::dotenv();

        Self {
            api_base_url: env::var("API_BASE_URL")
                .unwrap_or_else(|_| "https://api.xiaomimimo.com/v1".to_string()),
            api_key: env::var("API_KEY").unwrap_or_default(),
            username: env::var("USERNAME").unwrap_or_default(),
            password: env::var("PASSWORD").unwrap_or_default(),
            model: env::var("MODEL").unwrap_or_else(|_| "mimo-v2.5-tts".to_string()),
            default_voice: env::var("DEFAULT_VOICE").unwrap_or_else(|_| "晓晓".to_string()),
            default_style: env::var("DEFAULT_STYLE")
                .unwrap_or_else(|_| "温柔，语速适中".to_string()),
            timeout_secs: env::var("TIMEOUT_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(60),
            max_text_length: env::var("MAX_TEXT_LENGTH")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(5000),
            output_format: env::var("OUTPUT_FORMAT").unwrap_or_else(|_| "wav".to_string()),
            rate_limit_per_minute: env::var("RATE_LIMIT_PER_MINUTE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(60),
            max_request_size: env::var("MAX_REQUEST_SIZE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1_048_576),
            listen_addr: env::var("LISTEN_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:9880".to_string()),
            log_level: env::var("LOG_LEVEL").unwrap_or_else(|_| "info".to_string()),
        }
    }

    pub fn content_type(&self) -> &str {
        CONTENT_TYPE_MAP
            .iter()
            .find(|(fmt, _)| *fmt == self.output_format)
            .map(|(_, ct)| *ct)
            .unwrap_or("audio/wav")
    }

    pub fn auth_enabled(&self) -> bool {
        !self.username.is_empty() && !self.password.is_empty()
    }
}
