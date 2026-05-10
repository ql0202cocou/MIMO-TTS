mod api;
mod auth;
mod config;
mod error;
mod rate_limit;
mod sanitize;
mod security_headers;
mod tts;

use axum::http::Method;
use axum::routing::{get, post};
use axum::Router;
use std::net::SocketAddr;
use tower_http::cors::{Any, CorsLayer};
use tracing_subscriber::EnvFilter;

use crate::config::Settings;
use crate::rate_limit::RateLimiter;
use crate::tts::service::TtsService;

#[derive(Clone)]
pub struct AppState {
    pub tts: TtsService,
    pub rate_limiter: RateLimiter,
    pub settings: Settings,
}

#[tokio::main]
async fn main() {
    let settings = Settings::from_env();

    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new(&settings.log_level)),
        )
        .init();

    tracing::info!("========================================");
    tracing::info!("MIMO-TTS Legado Bridge starting...");
    tracing::info!(api_base_url = %settings.api_base_url);
    tracing::info!(default_voice = %settings.default_voice);
    tracing::info!(model = %settings.model);
    tracing::info!(output_format = %settings.output_format);
    tracing::info!(max_text_length = settings.max_text_length);
    tracing::info!(rate_limit = settings.rate_limit_per_minute);
    tracing::info!(max_request_size = settings.max_request_size);

    if settings.api_key.is_empty() {
        tracing::warn!("API_KEY is not configured! API calls will fail.");
    } else {
        tracing::info!("API_KEY is configured.");
    }

    if settings.auth_enabled() {
        tracing::info!("Basic Auth enabled.");
    } else {
        tracing::warn!("USERNAME/PASSWORD not configured! Service is open to all.");
    }

    tracing::info!(listen_addr = %settings.listen_addr);
    tracing::info!("========================================");

    let tts = TtsService::new(settings.clone());
    let rate_limiter = RateLimiter::new(settings.rate_limit_per_minute);

    let state = AppState {
        tts,
        rate_limiter,
        settings: settings.clone(),
    };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([Method::GET, Method::POST])
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(api::health::health_check))
        .route("/voices", get(api::voices::get_voices))
        .route("/speak", get(api::speak::speak_get))
        .route("/speak", post(api::speak::speak_post))
        .route("/legado", get(api::legado::legado_import))
        .layer(axum::middleware::from_fn(
            security_headers::security_headers_middleware,
        ))
        .layer(cors)
        .with_state(state);

    let addr: SocketAddr = settings
        .listen_addr
        .parse()
        .expect("Invalid listen address");

    tracing::info!(%addr, "Server listening");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("Failed to bind");

    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(shutdown_signal())
    .await
    .expect("Server failed");
}

async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("Failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }

    tracing::info!("Shutdown signal received");
}
