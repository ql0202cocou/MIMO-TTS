pub fn speed_to_hint(speed: u8) -> &'static str {
    match speed {
        0..=15 => "语速很慢，缓慢朗读",
        16..=25 => "语速较慢，从容朗读",
        26..=35 => "语速适中",
        36..=45 => "语速较快，紧凑朗读",
        _ => "语速很快，快速朗读",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_speed_ranges() {
        assert_eq!(speed_to_hint(5), "语速很慢，缓慢朗读");
        assert_eq!(speed_to_hint(15), "语速很慢，缓慢朗读");
        assert_eq!(speed_to_hint(16), "语速较慢，从容朗读");
        assert_eq!(speed_to_hint(25), "语速较慢，从容朗读");
        assert_eq!(speed_to_hint(26), "语速适中");
        assert_eq!(speed_to_hint(30), "语速适中");
        assert_eq!(speed_to_hint(35), "语速适中");
        assert_eq!(speed_to_hint(36), "语速较快，紧凑朗读");
        assert_eq!(speed_to_hint(45), "语速较快，紧凑朗读");
        assert_eq!(speed_to_hint(46), "语速很快，快速朗读");
        assert_eq!(speed_to_hint(50), "语速很快，快速朗读");
    }
}
