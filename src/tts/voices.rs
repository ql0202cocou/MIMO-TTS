use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct VoiceInfo {
    pub name: &'static str,
    pub voice_id: &'static str,
    pub language: &'static str,
    pub gender: &'static str,
}

pub const BUILTIN_VOICES: &[VoiceInfo] = &[
    VoiceInfo { name: "MiMo-默认", voice_id: "mimo_default", language: "中文", gender: "-" },
    VoiceInfo { name: "晓晓", voice_id: "晓晓", language: "中文", gender: "女" },
    VoiceInfo { name: "晓伊", voice_id: "晓伊", language: "中文", gender: "女" },
    VoiceInfo { name: "云阳", voice_id: "云阳", language: "中文", gender: "男" },
    VoiceInfo { name: "云逸", voice_id: "云逸", language: "中文", gender: "男" },
    VoiceInfo { name: "Mia", voice_id: "Mia", language: "英文", gender: "女" },
    VoiceInfo { name: "Chloe", voice_id: "Chloe", language: "英文", gender: "女" },
    VoiceInfo { name: "Milo", voice_id: "Milo", language: "英文", gender: "男" },
    VoiceInfo { name: "Dean", voice_id: "Dean", language: "英文", gender: "男" },
];

pub fn validate_voice(voice: Option<&str>, default: &str) -> String {
    match voice {
        Some(v) if BUILTIN_VOICES.iter().any(|info| info.voice_id == v) => v.to_string(),
        _ => {
            if voice.is_some() {
                tracing::warn!("Invalid voice requested, falling back to default");
            }
            default.to_string()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_voice() {
        assert_eq!(validate_voice(Some("晓晓"), "晓晓"), "晓晓");
        assert_eq!(validate_voice(Some("Mia"), "晓晓"), "Mia");
    }

    #[test]
    fn test_invalid_voice_fallback() {
        assert_eq!(validate_voice(Some("nonexistent"), "晓晓"), "晓晓");
    }

    #[test]
    fn test_none_voice_fallback() {
        assert_eq!(validate_voice(None, "晓晓"), "晓晓");
    }

    #[test]
    fn test_all_voices_valid() {
        for voice in BUILTIN_VOICES {
            assert_eq!(
                validate_voice(Some(voice.voice_id), "晓晓"),
                voice.voice_id
            );
        }
    }
}
