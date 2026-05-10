use axum::extract::State;
use axum::Json;

use crate::AppState;
use crate::auth::BasicAuth;

pub async fn get_voices(
    State(state): State<AppState>,
    _auth: BasicAuth,
) -> Json<serde_json::Value> {
    let voices = state.tts.get_voices();
    Json(serde_json::to_value(voices).unwrap())
}
