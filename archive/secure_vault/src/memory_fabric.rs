use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

/// Represents a single memory fragment that can be attached to a persona.
#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
pub struct MemoryFragment {
    /// Unique identifier for the fragment (e.g., UUID or timestamp‑based).
    pub id: String,
    /// The persona this fragment belongs to.
    pub persona_id: String,
    /// Unix epoch milliseconds when the fragment was created.
    pub timestamp: i64,
    /// Tags used for retrieval and filtering.
    pub tags: Vec<String>,
    /// The actual textual content of the fragment.
    pub content: String,
    /// Optional embedding vector for future similarity search.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embedding: Option<Vec<f32>>,
}

/// Helper struct for managing memory fragments on disk.
pub struct MemoryFabric {
    /// Base directory for all memory fragments: `$HOME/.codexify/memory/`.
    base_path: PathBuf,
}

impl MemoryFabric {
    /// Creates a new `MemoryFabric`, ensuring the base directory exists.
    pub fn new() -> io::Result<Self> {
        let home_dir = dirs::home_dir()
            .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "Home directory not found"))?;
        let base_path = home_dir.join(".codexify").join("memory");
        fs::create_dir_all(&base_path)?;
        Ok(Self { base_path })
    }

    /// Returns the directory for a specific persona.
    fn persona_dir(&self, persona_id: &str) -> PathBuf {
        self.base_path.join(persona_id)
    }

    /// Adds a new memory fragment. The fragment is serialized as JSON.
    pub fn add_fragment(&self, fragment: &MemoryFragment) -> io::Result<()> {
        let dir = self.persona_dir(&fragment.persona_id);
        fs::create_dir_all(&dir)?;
        let file_path = dir.join(format!("{}.json", fragment.id));
        let json = serde_json::to_string_pretty(&fragment)?;
        let mut file = fs::File::create(&file_path)?;
        file.write_all(json.as_bytes())?;
        Ok(())
    }

    /// Loads all fragments for a given persona.
    fn load_all(&self, persona_id: &str) -> io::Result<Vec<MemoryFragment>> {
        let dir = self.persona_dir(persona_id);
        if !dir.exists() {
            return Ok(vec![]);
        }
        let mut fragments = Vec::new();
        for entry in fs::read_dir(&dir)? {
            let entry = entry?;
            if entry.path().extension().and_then(|s| s.to_str()) != Some("json") {
                continue;
            }
            let data = fs::read_to_string(entry.path())?;
            let fragment: MemoryFragment = serde_json::from_str(&data)?;
            fragments.push(fragment);
        }
        Ok(fragments)
    }

    /// Retrieves fragments that contain **all** of the supplied tags.
    pub fn get_fragments_by_tags(
        &self,
        persona_id: &str,
        tags: &[String],
    ) -> io::Result<Vec<MemoryFragment>> {
        let all = self.load_all(persona_id)?;
        let filtered = all
            .into_iter()
            .filter(|f| tags.iter().all(|t| f.tags.contains(t)))
            .collect();
        Ok(filtered)
    }

    /// Simple keyword‑based search (mocked). Returns up to `top_k` fragments whose
    /// content contains the query string (case‑insensitive). In a real
    /// implementation this would use embeddings.
    pub fn search(
        &self,
        persona_id: &str,
        query: &str,
        top_k: usize,
    ) -> io::Result<Vec<MemoryFragment>> {
        let all = self.load_all(persona_id)?;
        let mut matches: Vec<MemoryFragment> = all
            .into_iter()
            .filter(|f| f.content.to_lowercase().contains(&query.to_lowercase()))
            .collect();
        matches.sort_by_key(|f| f.timestamp);
        matches.truncate(top_k);
        Ok(matches)
    }
}

// Unit tests for MemoryFabric
#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_fabric() -> MemoryFabric {
        // Use a temporary directory inside the system's temp dir.
        let temp_dir = std::env::temp_dir().join("memory_fabric_test");
        // Clean up any previous run.
        let _ = fs::remove_dir_all(&temp_dir);
        fs::create_dir_all(&temp_dir).unwrap();
        // Override the base_path for testing.
        MemoryFabric {
            base_path: temp_dir,
        }
    }

    fn sample_fragment(persona_id: &str, tags: &[&str], content: &str) -> MemoryFragment {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as i64;
        MemoryFragment {
            id: format!("{}-{}", persona_id, now),
            persona_id: persona_id.to_string(),
            timestamp: now,
            tags: tags.iter().map(|s| s.to_string()).collect(),
            content: content.to_string(),
            embedding: None,
        }
    }

    #[test]
    fn add_and_retrieve_by_tags() {
        let fabric = temp_fabric();
        let p1 = sample_fragment("alice", &[\"tag1\", \"tag2\"], \"First fragment\");
        let p2 = sample_fragment(\"alice\", &[\"tag2\"], \"Second fragment\");
        fabric.add_fragment(&p1).unwrap();
        fabric.add_fragment(&p2).unwrap();

        let result = fabric
            .get_fragments_by_tags(\"alice\", &[\"tag2\".to_string()])
            .unwrap();
        assert_eq!(result.len(), 2);
        let result = fabric
            .get_fragments_by_tags(\"alice\", &[\"tag1\".to_string(), \"tag2\".to_string()])
            .unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].content, \"First fragment\");
    }

    #[test]
    fn search_fragments() {
        let fabric = temp_fabric();
        let p1 = sample_fragment(\"bob\", &[\"a\"], \"The quick brown fox\");
        let p2 = sample_fragment(\"bob\", &[\"b\"], \"jumps over the lazy dog\");
        fabric.add_fragment(&p1).unwrap();
        add_memory_fragment(&p2).unwrap();

        let result = fabric.search(\"bob\", \"quick\", 10).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].content, \"The quick brown fox\");
    }
}
