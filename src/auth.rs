use axum::extract::FromRequestParts;
use axum::http::request::Parts;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use subtle::ConstantTimeEq;

use crate::config::Settings;

pub struct BasicAuth;

impl<S> FromRequestParts<S> for BasicAuth
where
    S: Send + Sync,
{
    type Rejection = Response;

    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        // Get settings from extensions (set during request processing)
        let settings = parts
            .extensions
            .get::<Settings>()
            .cloned()
            .unwrap_or_else(|| Settings::from_env());

        // If auth is not configured, allow all requests
        if !settings.auth_enabled() {
            return Ok(BasicAuth);
        }

        let auth_header = parts
            .headers
            .get("Authorization")
            .and_then(|v| v.to_str().ok());

        match auth_header {
            Some(header) if header.starts_with("Basic ") => {
                let encoded = &header[6..];
                match STANDARD.decode(encoded) {
                    Ok(decoded) => {
                        let credentials = String::from_utf8_lossy(&decoded);
                        let mut split = credentials.splitn(2, ':');
                        let username = split.next().unwrap_or("");
                        let password = split.next().unwrap_or("");

                        let username_ok = username.as_bytes().ct_eq(settings.username.as_bytes());
                        let password_ok = password.as_bytes().ct_eq(settings.password.as_bytes());

                        if bool::from(username_ok & password_ok) {
                            Ok(BasicAuth)
                        } else {
                            Err(reject_auth())
                        }
                    }
                    Err(_) => Err(reject_auth()),
                }
            }
            _ => Err(reject_auth()),
        }
    }
}

fn reject_auth() -> Response {
    let mut response = (
        StatusCode::UNAUTHORIZED,
        axum::Json(serde_json::json!({ "detail": "Invalid credentials" })),
    )
        .into_response();

    response.headers_mut().insert(
        "WWW-Authenticate",
        "Basic realm=\"MIMO-TTS\"".parse().unwrap(),
    );

    response
}
