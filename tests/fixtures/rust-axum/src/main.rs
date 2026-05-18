// Synthetic fixture — intentionally contains stub patterns for the audit harness.

use axum::{routing::post, Router};

async fn charge_handler() -> &'static str {
    // HIGH: handler uses todo!() macro in a user-reachable path.
    todo!("billing not wired yet")
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/charge", post(charge_handler));
    let _ = app;
}
