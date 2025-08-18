use tauri::command; use reqwest::Client;
#[command]
async fn api_post(path: String, body: String, base: String, token: Option<String>) -> Result<String,String> {
  let client = Client::new();
  let mut req = client.post(format!("{}/{}", base.trim_end_matches('/'), path.trim_start_matches('/')))
      .header("Content-Type","application/json");
  if let Some(t)=token { req = req.header("Authorization", format!("Bearer {}", t)); }
  let res = req.body(body).send().await.map_err(|e|e.to_string())?;
  let status = res.status(); let txt = res.text().await.map_err(|e|e.to_string())?;
  if !status.is_success(){ return Err(txt); } Ok(txt)
}
