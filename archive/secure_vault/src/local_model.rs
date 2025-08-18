/// LocalModel integration for Codexify desktop app.
/// Provides async HTTP client to interact with Ollama / LocalAI servers.
///
/// The client supports:
/// - `/api/generate` for text generation
/// - `/api/tags` to list installed models
/// - `/api/embeddings` (optional)
/// - `/v1/chat/completions` when OpenAI mode is enabled
///
/// All functions return `Result` with a JSON string or a vector of model names.
/// Errors are propagated as strings for easy propagation to Tauri commands.

use crate::local_model_config::Config;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// The default Ollama endpoint.
const DEFAULT_BASE_URL: &str = "http://localhost:11434";

#[derive(Debug, Serialize, Deserialize)]
pub struct GenerateRequest {
    pub model: String,
    pub prompt: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stream: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub options: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GenerateResponse {
    pub model: String,
    pub created_at: String,
    pub response: String,
    pub done: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub done_reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub total_duration: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub load_duration: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub prompt_eval_count: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub eval_count: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub eval_duration: Option<u64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Tag {
    pub name: String,
    pub model: String,
    pub size: u64,
    pub digest: String,
    pub details: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TagsResponse {
    pub models: Vec<Tag>,
}

/// Generate text using the configured local model.
///
/// # Arguments
///
/// * `prompt` - The user prompt to send to the model.
/// * `config` - The current configuration (base URL, model name, mode).
///
/// Returns the generated text as a `String`.
pub async fn generate(prompt: &str, config: &Config) -> Result<String, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {}", e))?;

    let url = format!("{}/api/generate", config.base_url.as_deref().unwrap_or(DEFAULT_BASE_URL));

    let request_body = GenerateRequest {
        model: config
            .preferred_model
            .clone()
            .ok_or_else(|| "No preferred model set".to_string())?,
        prompt: prompt.to_string(),
        stream: Some(false),
        options: None,
    };

    let resp = client
        .post(&url)
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("HTTP request error: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!(
            "Server returned error status: {}",
            resp.status()
        ));
    }

    let resp_json: GenerateResponse = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse JSON: {}", e))?;

    Ok(resp_json.response)
}

/// List installed models from the local server.
///
/// Returns a vector of model names.
pub async fn list_models(config: &Config) -> Result<Vec<String>, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {}", e))?;

    let url = format!("{}/api/tags", config.base_url.as_deref().unwrap_or(DEFAULT_BASE_URL));

    let resp = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("HTTP request error: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Server returned error: {}", resp.status()));
    }

    let tags: TagsResponse = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse tags JSON: {}", e))?;

    Ok(tags.models.iter().map(|t| t.name.clone()).collect())
}

/// Check the health of the local server.
///
/// Returns `true` if the server responds to a simple request.
pub async fn health_check(config: &Config) -> Result<bool, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {}", e))?;

    let url = config.base_url.as_deref().unwrap_or(DEFAULT_BASE_URL);
    let resp = client.get(url).send().await;

    match resp {
        Ok(r) if r.status().is_success() => Ok(true),
        Ok(r) => Err(format!("Server responded with status {}", r.status())),
        Err(e) => Err(format!("Health check failed: {}", e)),
    }
}
