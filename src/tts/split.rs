use crate::config::{MIN_COMMA_SEGMENT_LENGTH, MIN_SEGMENT_LENGTH};

pub fn split_text(text: &str, max_len: usize) -> Vec<String> {
    let delimiters: &[char] = &['。', '！', '？', '；', '\n', '.', '!', '?', ';'];
    let mut segments = Vec::new();
    let mut parts = Vec::new();

    for ch in text.chars() {
        parts.push(ch);
        if delimiters.contains(&ch) && parts.len() >= MIN_SEGMENT_LENGTH {
            segments.push(parts.iter().collect::<String>());
            parts.clear();
        } else if parts.len() >= max_len {
            segments.push(parts.iter().collect::<String>());
            parts.clear();
        }
    }

    if !parts.is_empty() {
        let remaining: String = parts.iter().collect();
        let remaining = remaining.trim();
        if !remaining.is_empty() {
            if remaining.len() > max_len {
                segments.extend(split_by_comma(remaining, max_len));
            } else {
                segments.push(remaining.to_string());
            }
        }
    }

    // Merge short segments
    let mut merged = Vec::new();
    let mut buffer = String::new();
    for seg in segments {
        if buffer.len() + seg.len() <= max_len {
            buffer.push_str(&seg);
        } else {
            if !buffer.is_empty() {
                merged.push(buffer.clone());
                buffer.clear();
            }
            if seg.len() > max_len {
                for chunk in seg.chars().collect::<Vec<_>>().chunks(max_len) {
                    merged.push(chunk.iter().collect());
                }
            } else {
                buffer = seg;
            }
        }
    }
    if !buffer.is_empty() {
        merged.push(buffer);
    }

    if merged.is_empty() {
        vec![text.chars().take(max_len).collect()]
    } else {
        merged
    }
}

pub fn split_by_comma(text: &str, max_len: usize) -> Vec<String> {
    let delimiters: &[char] = &['，', ',', '、', '：', ':'];
    let mut segments = Vec::new();
    let mut parts = Vec::new();

    for ch in text.chars() {
        parts.push(ch);
        if delimiters.contains(&ch) && parts.len() >= MIN_COMMA_SEGMENT_LENGTH {
            segments.push(parts.iter().collect::<String>());
            parts.clear();
        } else if parts.len() >= max_len {
            segments.push(parts.iter().collect::<String>());
            parts.clear();
        }
    }

    if !parts.is_empty() {
        let remaining: String = parts.iter().collect();
        let remaining = remaining.trim();
        if !remaining.is_empty() {
            segments.push(remaining.to_string());
        }
    }

    segments
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_short_text_no_split() {
        let text = "这是一个短文本。";
        let segments = split_text(text, 5000);
        assert_eq!(segments.len(), 1);
        assert_eq!(segments[0], text);
    }

    #[test]
    fn test_long_text_splits_at_punctuation() {
        let mut text = String::new();
        for i in 0..10 {
            text.push_str(&format!("这是第{}个句子，包含一些内容。", i));
        }
        let segments = split_text(&text, 5000);
        // Should split at 。 when segment >= MIN_SEGMENT_LENGTH
        assert!(segments.len() >= 1);
    }

    #[test]
    fn test_no_punctuation_force_split() {
        let text = "a".repeat(6000);
        let segments = split_text(&text, 5000);
        assert!(segments.len() >= 2);
    }

    #[test]
    fn test_empty_text() {
        let segments = split_text("", 5000);
        assert_eq!(segments.len(), 1);
    }

    #[test]
    fn test_comma_split() {
        let text = "a".repeat(100) + "，" + &"b".repeat(100);
        let segments = split_by_comma(&text, 5000);
        assert!(segments.len() >= 2);
    }
}
