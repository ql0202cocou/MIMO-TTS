use dashmap::DashMap;
use std::net::IpAddr;
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::Mutex;

struct TokenBucket {
    tokens: f64,
    last_refill: Instant,
    max_tokens: f64,
    refill_rate: f64, // tokens per second
}

impl TokenBucket {
    fn new(max_per_minute: u32) -> Self {
        Self {
            tokens: max_per_minute as f64,
            last_refill: Instant::now(),
            max_tokens: max_per_minute as f64,
            refill_rate: max_per_minute as f64 / 60.0,
        }
    }

    fn try_acquire(&mut self) -> bool {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last_refill).as_secs_f64();
        self.tokens = (self.tokens + elapsed * self.refill_rate).min(self.max_tokens);
        self.last_refill = now;

        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            true
        } else {
            false
        }
    }
}

#[derive(Clone)]
pub struct RateLimiter {
    buckets: Arc<DashMap<IpAddr, Arc<Mutex<TokenBucket>>>>,
    max_per_minute: u32,
}

impl RateLimiter {
    pub fn new(max_per_minute: u32) -> Self {
        Self {
            buckets: Arc::new(DashMap::new()),
            max_per_minute,
        }
    }

    pub async fn check(&self, ip: IpAddr) -> bool {
        let bucket = self
            .buckets
            .entry(ip)
            .or_insert_with(|| Arc::new(Mutex::new(TokenBucket::new(self.max_per_minute))))
            .clone();

        bucket.lock().await.try_acquire()
    }

    pub fn extract_client_ip(headers: &axum::http::HeaderMap, trust_proxy: bool) -> IpAddr {
        if trust_proxy {
            if let Some(forwarded) = headers.get("X-Forwarded-For").and_then(|v| v.to_str().ok())
            {
                if let Some(first) = forwarded.split(',').next() {
                    if let Ok(ip) = first.trim().parse::<IpAddr>() {
                        return ip;
                    }
                }
            }
            if let Some(real_ip) = headers.get("X-Real-IP").and_then(|v| v.to_str().ok()) {
                if let Ok(ip) = real_ip.trim().parse::<IpAddr>() {
                    return ip;
                }
            }
        }
        // Fallback - in production this would come from the socket addr
        "127.0.0.1".parse().unwrap()
    }
}
