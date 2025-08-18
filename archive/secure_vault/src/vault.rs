use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::PathBuf;
use std::sync::Mutex;

use base64::{engine::general_purpose, Engine as _};
use rand::RngCore;
use rand::rngs::OsRng;
use ring::aead::{self, Aad, BoundKey, LessSafeKey, Nonce, UnboundKey, AES_256_GCM};
use once_cell::sync::Lazy;
use uuid::Uuid;

use crate::desktop_keyring::CodexifyDesktopKeyring;

/// Path to the encrypted vault file (compatible with Python implementation)
static IDDB_PATH: Lazy<PathBuf> = Lazy::new(|| {
    let home = dirs::home_dir().expect("Unable to locate home directory");
    home.join(".codexify_iddb.enc")
});

/// Path to the backup file (burn‑on‑rekey)
static BACKUP_PATH: Lazy<PathBuf> = Lazy::new(|| {
    let home = dirs::home_dir().expect("Unable to locate home directory");
    home.join(".codexify_iddb.backup.enc")
});

pub struct Vault;

impl Vault {
    /// Retrieve the device key from the OS keyring.
    fn get_key() -> Result<Vec<u8>, String> {
        CodexifyDesktopKeyring::retrieve_key().map_err(|e| format!("Key retrieval error: {}", e))
    }

    /// Store a raw 32‑byte key in the keyring.
    pub fn store_key(key: &[u8]) -> Result<(), String> {
        CodexifyDesktopKeyring::store_key(key).map_err(|e| format!("Key store error: {}", e))
    }

    /// Encrypt data using AES‑256‑GCM.
    /// Returns `nonce || ciphertext || tag`.
    pub fn encrypt(plaintext: &[u8]) -> Result<Vec<u8>, String> {
        let key = Self::get_key()?;
        let unbound_key = UnboundKey::new(&AES_256_GCM, &key).map_err(|e| format!("UnboundKey error: {:?}", e))?;
        let less_key = LessSafeKey::new(unbound_key);

        // Generate a fresh 12‑byte nonce.
        let mut nonce_bytes = [0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::assume_unique_for_key(nonce_bytes);

        // Prepare buffer with plaintext.
        let mut in_out = plaintext.to_vec();
        // Encrypt in place, appending the tag.
        less_key
            .seal_in_place_append_tag(nonce, Aad::empty(), &mut in_out)
            .map_err(|e| format!("Encryption error: {:?}", e))?;

        // Prepend nonce to the ciphertext+tag.
        let mut result = Vec::with_capacity(12 + in_out.len());
        result.extend_from_slice(&nonce_bytes);
        result.extend_from_slice(&in_out);
        Ok(result)
    }

    /// Decrypt data produced by `encrypt`.
    pub fn decrypt(ciphertext: &[u8]) -> Result<Vec<u8>, String> {
        if ciphertext.len() < 12 + 16 {
            return Err("Ciphertext too short".into());
        }
        let key = Self::get_key()?;
        let unbound_key = UnboundKey::new(&AES_256_GCM, &key).map_err(|e| format!("UnboundKey error: {:?}", e))?;
        let less_key = LessSafeKey::new(unbound_key);

        // Split nonce and ciphertext+tag.
        let (nonce_bytes, ct_tag) = ciphertext.split_at(12);
        let nonce = Nonce::assume_unique_for_key({
            let mut arr = [0u8; 12];
            arr.copy_from_slice(nonce_bytes);
            arr
        });

        let mut buffer = ct_tag.to_vec();
        less_key
            .open_in_place(nonce, Aad::empty(), &mut buffer)
            .map_err(|e| format!("Decryption error: {:?}", e))?;
        // The buffer now contains the plaintext.
        Ok(buffer)
    }

    /// Export the encrypted vault file (still encrypted).
    pub fn export() -> Result<Vec<u8>, String> {
        let mut file = File::open(&*IDDB_PATH).map_err(|e| format!("Open error: {}", e))?;
        let mut data = Vec::new();
        file.read_to_end(&mut data).map_err(|e| format!("Read error: {}", e))?;
        Ok(data)
    }

    /// Import an encrypted vault, securely shredding the old one.
    pub fn import(data: &[u8]) -> Result<(), String> {
        // Shred existing file if present.
        if IDDB_PATH.exists() {
            Self::shred_file(&*IDDB_PATH)?;
        }
        // Write new encrypted data.
        let mut file = File::create(&*IDDB_PATH).map_err(|e| format!("Create error: {}", e))?;
        file.write_all(data).map_err(|e| format!("Write error: {}", e))?;
        Ok(())
    }

    /// Securely shred a file (overwrite with random data then delete).
    fn shred_file(path: &PathBuf) -> Result<(), String> {
        if let Ok(metadata) = fs::metadata(path) {
            let size = metadata.len() as usize;
            let mut rng = OsRng;
            let mut random_data = vec![0u8; size];
            rng.fill_bytes(&mut random_data);
            let mut file = File::create(path).map_err(|e| format!("Shred open error: {}", e))?;
            file.write_all(&random_data).map_err(|e| format!("Shred write error: {}", e))?;
        }
        fs::remove_file(path).map_err(|e| format!("Remove error: {}", e))?;
        // Also delete key from keyring.
        CodexifyDesktopKeyring::delete_key().map_err(|e| format!("Key delete error: {}", e))?;
        Ok(())
    }

    /// Public API to shred the vault and delete the key.
    pub fn shred() -> Result<(), String> {
        Self::shred_file(&*IDDB_PATH)?;
        // Delete key from keyring.
        CodexifyDesktopKeyring::delete_key().map_err(|e| format!("Key delete error: {}", e))
    }
}
