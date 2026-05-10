use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tokio::time::{sleep, Duration};

use super::speed::speed_to_hint;
use super::split::split_text;
use super::voices::{validate_voice, BUILTIN_VOICES};
use super::wav::concatenate_wav;
use crate::config::Settings;

const MAX_RETRIES: u32 = 3;
const RETRY_DELAY: f64 = 1.0;

#[derive(Clone)]
pub struct TtsService {
    client: Client,
    settings: Settings,
}

#[derive(Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<Message>,
    audio: AudioConfig,
}

#[derive(Serialize)]
struct Message {
    role: String,
    content: String,
}

#[derive(Serialize)]
struct AudioConfig {
    format: String,
    voice: String,
}

#[derive(Deserialize)]
struct ChatResponse {
    choices: Vec<Choice>,
}

#[derive(Deserialize)]
struct Choice {
    message: ChoiceMessage,
}

#[derive(Deserialize)]
struct ChoiceMessage {
    audio: Option<AudioData>,
}

#[derive(Deserialize)]
struct AudioData {
    data: String,
}

impl TtsService {
    pub fn new(settings: Settings) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(settings.timeout_secs))
            .build()
            .expect("Failed to create HTTP client");

        Self { client, settings }
    }

    pub async fn synthesize_long_text(
        &self,
        text: &str,
        voice: Option<&str>,
        style_hint: Option<&str>,
        speed: Option<u8>,
    ) -> Result<Vec<u8>, String> {
        if text.len() <= self.settings.max_text_length {
            return self.synthesize(text, voice, style_hint, speed).await;
        }

        let segments = split_text(text, self.settings.max_text_length);
        tracing::info!(segments = segments.len(), "Long text split into segments");

        let mut audio_parts = Vec::new();
        for (i, segment) in segments.iter().enumerate() {
            tracing::info!(
                segment = i + 1,
                total = segments.len(),
                length = segment.len(),
                "Synthesizing segment"
            );
            let audio = self.synthesize(segment, voice, style_hint, speed).await?;
            audio_parts.push(audio);
        }

        if self.settings.output_format == "wav" {
            concatenate_wav(&audio_parts).map_err(|e| format!("WAV concatenation failed: {e}"))
        } else {
            Ok(audio_parts.into_iter().flatten().collect())
        }
    }

    async fn synthesize(
        &self,
        text: &str,
        voice: Option<&str>,
        style_hint: Option<&str>,
        speed: Option<u8>,
    ) -> Result<Vec<u8>, String> {
        let voice = validate_voice(voice, &self.settings.default_voice);

        // Build style instruction
        let mut style_parts = Vec::new();
        if let Some(hint) = style_hint {
            if !hint.is_empty() {
                style_parts.push(hint.to_string());
            }
        }
        if let Some(s) = speed {
            style_parts.push(speed_to_hint(s).to_string());
        }
        if style_parts.is_empty() && !self.settings.default_style.is_empty() {
            style_parts.push(self.settings.default_style.clone());
        }

        let combined_style = if style_parts.is_empty() {
            None
        } else {
            Some(style_parts.join("，"))
        };

        // Build messages
        let mut messages = Vec::new();
        if let Some(ref style) = combined_style {
            messages.push(Message {
                role: "user".to_string(),
                content: style.clone(),
            });
        }
        messages.push(Message {
            role: "assistant".to_string(),
            content: text.to_string(),
        });

        tracing::info!(
            model = self.settings.model,
            voice = voice,
            format = self.settings.output_format,
            style = combined_style.as_deref().unwrap_or("none"),
            text_length = text.len(),
            "Calling MIMO-TTS API"
        );

        let request = ChatRequest {
            model: self.settings.model.clone(),
            messages,
            audio: AudioConfig {
                format: self.settings.output_format.clone(),
                voice,
            },
        };

        let url = format!("{}/v1/chat/completions", self.settings.api_base_url);

        let mut last_error = None;
        for attempt in 1..=MAX_RETRIES {
            match self.call_api(&url, &request).await {
                Ok(audio) => return Ok(audio),
                Err(e) => {
                    if !is_retryable(&e) {
                        tracing::error!(error = %e, "Non-retryable API error");
                        return Err(e);
                    }
                    if attempt < MAX_RETRIES {
                        let wait = RETRY_DELAY * attempt as f64;
                        tracing::warn!(
                            attempt,
                            max = MAX_RETRIES,
                            error = %e,
                            wait_secs = wait,
                            "API call failed, retrying"
                        );
                        sleep(Duration::from_secs_f64(wait)).await;
                    } else {
                        tracing::error!(error = %e, "API call failed after all retries");
                    }
                    last_error = Some(e);
                }
            }
        }

        Err(last_error.unwrap_or_else(|| "TTS synthesis failed".to_string()))
    }

    async fn call_api(&self, url: &str, request: &ChatRequest) -> Result<Vec<u8>, String> {
        let response = self
            .client
            .post(url)
            .header("Authorization", format!("Bearer {}", self.settings.api_key))
            .header("Content-Type", "application/json")
            .json(request)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {e}"))?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            return Err(format!("API returned {status}: {body}"));
        }

        let chat_response: ChatResponse = response
            .json()
            .await
            .map_err(|e| format!("Failed to parse API response: {e}"))?;

        let choice = chat_response
            .choices
            .first()
            .ok_or_else(|| "API returned empty choices list".to_string())?;

        let audio_data = choice
            .message
            .audio
            .as_ref()
            .ok_or_else(|| "API returned no audio data".to_string())?;

        let audio_bytes = STANDARD
            .decode(&audio_data.data)
            .map_err(|e| format!("Failed to decode base64 audio: {e}"))?;

        tracing::info!(size = audio_bytes.len(), "MIMO-TTS API response received");
        Ok(audio_bytes)
    }

    pub fn get_voices(&self) -> &'static [super::voices::VoiceInfo] {
        BUILTIN_VOICES
    }

    pub fn settings(&self) -> &Settings {
        &self.settings
    }
}

fn is_retryable(error: &str) -> bool {
    error.contains("timeout")
        || error.contains("connection")
        || error.contains("5")
            && (error.contains("500")
                || error.contains("502")
                || error.contains("503")
                || error.contains("504"))
}
