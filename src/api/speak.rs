use axum::body::Body;
use axum::extract::{Query, State};
use axum::http::{HeaderValue, StatusCode};
use axum::response::Response;
use axum::Json;
use serde::Deserialize;

use crate::AppState;
use crate::auth::BasicAuth;
use crate::config::{SPEED_DEFAULT, SPEED_MAX, SPEED_MIN};
use crate::error::AppError;
use crate::sanitize::{sanitize_style, sanitize_text, sanitize_voice};

#[derive(Deserialize)]
pub struct SpeakQuery {
    pub text: String,
    #[serde(default = "default_speed")]
    pub speed: u8,
    pub voice: Option<String>,
    pub style: Option<String>,
}

fn default_speed() -> u8 {
    SPEED_DEFAULT
}

#[derive(Deserialize)]
pub struct SpeakBody {
    pub text: String,
    #[serde(default = "default_speed")]
    pub speed: u8,
    pub voice: Option<String>,
    pub style: Option<String>,
}

pub async fn speak_get(
    State(state): State<AppState>,
    _auth: BasicAuth,
    Query(params): Query<SpeakQuery>,
) -> Result<Response, AppError> {
    let text = sanitize_text(&params.text);
    if text.is_empty() {
        return Err(AppError::BadRequest("文本不能为空".to_string()));
    }
    if params.speed < SPEED_MIN || params.speed > SPEED_MAX {
        return Err(AppError::BadRequest(format!(
            "speed must be between {SPEED_MIN} and {SPEED_MAX}"
        )));
    }
    let voice = params.voice.as_deref().map(sanitize_voice);
    let style = params.style.as_deref().map(sanitize_style);

    handle_speak(&state, &text, params.speed, voice.as_deref(), style.as_deref()).await
}

pub async fn speak_post(
    State(state): State<AppState>,
    _auth: BasicAuth,
    Json(body): Json<SpeakBody>,
) -> Result<Response, AppError> {
    let text = sanitize_text(&body.text);
    if text.is_empty() {
        return Err(AppError::BadRequest("文本不能为空".to_string()));
    }
    if body.speed < SPEED_MIN || body.speed > SPEED_MAX {
        return Err(AppError::BadRequest(format!(
            "speed must be between {SPEED_MIN} and {SPEED_MAX}"
        )));
    }
    let voice = body.voice.as_deref().map(sanitize_voice);
    let style = body.style.as_deref().map(sanitize_style);

    handle_speak(&state, &text, body.speed, voice.as_deref(), style.as_deref()).await
}

async fn handle_speak(
    state: &AppState,
    text: &str,
    speed: u8,
    voice: Option<&str>,
    style: Option<&str>,
) -> Result<Response, AppError> {
    tracing::info!(text_length = text.len(), speed, voice, style, "/speak request");

    let audio_data = state
        .tts
        .synthesize_long_text(text, voice, style, Some(speed))
        .await
        .map_err(|e| AppError::UpstreamFailure(anyhow::anyhow!(e)))?;

    let content_type = state.tts.settings().content_type();

    let response = Response::builder()
        .status(StatusCode::OK)
        .header("Content-Type", HeaderValue::from_str(content_type).unwrap())
        .body(Body::from(audio_data))
        .unwrap();

    Ok(response)
}
