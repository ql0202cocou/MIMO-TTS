use axum::extract::ConnectInfo;
use axum::http::HeaderMap;
use axum::Json;
use serde_json::{json, Value};
use std::net::SocketAddr;

pub async fn legado_import(
    headers: HeaderMap,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
) -> Json<Value> {
    let host = headers
        .get("Host")
        .and_then(|v| v.to_str().ok())
        .map(|h| h.to_string())
        .unwrap_or_else(|| addr.to_string());

    let base_url = format!("http://{host}");

    let get_url = |voice: Option<&str>, style: Option<&str>| -> String {
        let mut url = format!("{base_url}/speak?text={{{{speakText}}}}&speed={{{{speakSpeed}}}}");
        if let Some(v) = voice {
            url.push_str(&format!("&voice={v}"));
        }
        if let Some(s) = style {
            url.push_str(&format!("&style={s}"));
        }
        url
    };

    let post_url = format!("{base_url}/speak,") + r###"{"method":"POST","headers":{"Content-Type":"application/json"},"body":"{\"text\":\"{{speakText}}\",\"speed\":{{speakSpeed}}}"}"###;

    let now = 1714567890123_i64;

    let engines = json!([
        {
            "id": now,
            "name": "MIMO-TTS 晓晓（默认）",
            "url": get_url(None, None),
            "contentType": "audio/wav",
            "concurrentRate": "0",
            "loginUrl": null,
            "loginUi": null,
            "header": null,
            "loginCheckJs": null,
            "lastUpdateTime": now
        },
        {
            "id": now + 1,
            "name": "MIMO-TTS 晓伊（女声）",
            "url": get_url(Some("晓伊"), None),
            "contentType": "audio/wav",
            "concurrentRate": "0",
            "loginUrl": null,
            "loginUi": null,
            "header": null,
            "loginCheckJs": null,
            "lastUpdateTime": now + 1
        },
        {
            "id": now + 2,
            "name": "MIMO-TTS 云阳（男声）",
            "url": get_url(Some("云阳"), None),
            "contentType": "audio/wav",
            "concurrentRate": "0",
            "loginUrl": null,
            "loginUi": null,
            "header": null,
            "loginCheckJs": null,
            "lastUpdateTime": now + 2
        },
        {
            "id": now + 3,
            "name": "MIMO-TTS 云逸（男声）",
            "url": get_url(Some("云逸"), None),
            "contentType": "audio/wav",
            "concurrentRate": "0",
            "loginUrl": null,
            "loginUi": null,
            "header": null,
            "loginCheckJs": null,
            "lastUpdateTime": now + 3
        },
        {
            "id": now + 4,
            "name": "MIMO-TTS 长文本模式（POST）",
            "url": post_url,
            "contentType": "audio/wav",
            "concurrentRate": "0",
            "loginUrl": null,
            "loginUi": null,
            "header": null,
            "loginCheckJs": null,
            "lastUpdateTime": now + 4
        },
        {
            "id": now + 5,
            "name": "MIMO-TTS 英文 Mia",
            "url": get_url(Some("Mia"), Some("自然流畅")),
            "contentType": "audio/wav",
            "concurrentRate": "0",
            "loginUrl": null,
            "loginUi": null,
            "header": null,
            "loginCheckJs": null,
            "lastUpdateTime": now + 5
        }
    ]);

    Json(engines)
}
