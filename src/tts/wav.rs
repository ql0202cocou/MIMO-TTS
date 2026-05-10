use hound::{WavReader, WavSpec, WavWriter};
use std::io::Cursor;

pub fn concatenate_wav(wav_parts: &[Vec<u8>]) -> Result<Vec<u8>, String> {
    if wav_parts.len() == 1 {
        return Ok(wav_parts[0].clone());
    }

    // Read spec from first WAV
    let reader =
        WavReader::new(Cursor::new(&wav_parts[0])).map_err(|e| format!("Failed to read WAV part 1: {e}"))?;
    let spec = reader.spec();

    let mut all_samples: Vec<i16> = Vec::new();

    // Read first part samples
    let reader =
        WavReader::new(Cursor::new(&wav_parts[0])).map_err(|e| format!("Failed to read WAV part 1: {e}"))?;
    for sample in reader.into_samples::<i16>() {
        let s = sample.map_err(|e| format!("Failed to read sample from WAV part 1: {e}"))?;
        all_samples.push(s);
    }

    // Read remaining parts and validate spec consistency
    for (idx, part) in wav_parts.iter().enumerate().skip(1) {
        let part_num = idx + 1;
        let reader = WavReader::new(Cursor::new(part))
            .map_err(|e| format!("Failed to read WAV part {part_num}: {e}"))?;
        let part_spec = reader.spec();

        if part_spec.channels != spec.channels
            || part_spec.sample_rate != spec.sample_rate
            || part_spec.bits_per_sample != spec.bits_per_sample
        {
            return Err(format!(
                "WAV part {part_num} has different audio params ({}ch/{}Hz/{}B) vs part 1 ({}ch/{}Hz/{}B)",
                part_spec.channels, part_spec.sample_rate, part_spec.bits_per_sample,
                spec.channels, spec.sample_rate, spec.bits_per_sample
            ));
        }

        let reader = WavReader::new(Cursor::new(part))
            .map_err(|e| format!("Failed to read WAV part {part_num}: {e}"))?;
        for sample in reader.into_samples::<i16>() {
            let s = sample.map_err(|e| format!("Failed to read sample from WAV part {part_num}: {e}"))?;
            all_samples.push(s);
        }
    }

    // Write combined WAV
    let mut output = Vec::new();
    {
        let mut writer = WavWriter::new(Cursor::new(&mut output), spec)
            .map_err(|e| format!("Failed to create WAV writer: {e}"))?;
        for &sample in &all_samples {
            writer
                .write_sample(sample)
                .map_err(|e| format!("Failed to write sample: {e}"))?;
        }
        writer
            .finalize()
            .map_err(|e| format!("Failed to finalize WAV: {e}"))?;
    }

    Ok(output)
}

/// Create a minimal valid WAV file for testing
#[cfg(test)]
pub fn make_test_wav(num_samples: u16, sample_rate: u32) -> Vec<u8> {
    let spec = WavSpec {
        channels: 1,
        sample_rate,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };
    let mut output = Vec::new();
    {
        let mut writer = WavWriter::new(Cursor::new(&mut output), spec).unwrap();
        for i in 0..num_samples {
            writer.write_sample((i as i16).wrapping_mul(100)).unwrap();
        }
        writer.finalize().unwrap();
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_wav_passthrough() {
        let wav = make_test_wav(100, 24000);
        let result = concatenate_wav(&[wav.clone()]).unwrap();
        assert_eq!(result, wav);
    }

    #[test]
    fn test_multiple_wav_concatenation() {
        let wav1 = make_test_wav(100, 24000);
        let wav2 = make_test_wav(200, 24000);
        let result = concatenate_wav(&[wav1, wav2]).unwrap();

        // Verify result is a valid WAV with combined samples
        let reader = WavReader::new(Cursor::new(&result)).unwrap();
        assert_eq!(reader.len(), 300);
    }

    #[test]
    fn test_mismatched_params_error() {
        let wav1 = make_test_wav(100, 24000);
        let wav2 = make_test_wav(100, 44100); // Different sample rate
        let result = concatenate_wav(&[wav1, wav2]);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("different audio params"));
    }
}
