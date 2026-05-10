use axum::Json;
use serde_json::{json, Value};

use crate::config::VERSION;

pub async fn health_check() -> Json<Value> {
    Json(json!({
        "status": "ok",
        "version": VERSION
    }))
}
