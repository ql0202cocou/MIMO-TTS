use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::json;

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("bad request: {0}")]
    BadRequest(String),

    #[error("unauthorized")]
    Unauthorized,

    #[error("too many requests")]
    TooManyRequests,

    #[error("upstream failure")]
    UpstreamFailure(#[source] anyhow::Error),

    #[error("internal error")]
    InternalError(#[source] anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            AppError::Unauthorized => (
                StatusCode::UNAUTHORIZED,
                "Invalid credentials".to_string(),
            ),
            AppError::TooManyRequests => {
                (StatusCode::TOO_MANY_REQUESTS, "Rate limit exceeded".to_string())
            }
            AppError::UpstreamFailure(e) => {
                tracing::error!("Upstream TTS API failure: {e:#}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "语音合成失败，请稍后重试".to_string(),
                )
            }
            AppError::InternalError(e) => {
                tracing::error!("Internal error: {e:#}");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "语音合成失败，请稍后重试".to_string(),
                )
            }
        };

        let body = Json(json!({ "detail": message }));
        let mut response = (status, body).into_response();

        if matches!(self, AppError::Unauthorized) {
            response.headers_mut().insert(
                "WWW-Authenticate",
                "Basic realm=\"MIMO-TTS\"".parse().unwrap(),
            );
        }

        response
    }
}
