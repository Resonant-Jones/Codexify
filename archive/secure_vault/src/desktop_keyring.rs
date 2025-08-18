use keyring::Keyring;
use std::error::Error;

/// Wrapper around the `keyring` crate to store a 32‑byte device key
/// in the OS credential store. The key is stored as a base64
/// string, mirroring the Python implementation.
pub struct CodexifyDesktopKeyring;

impl CodexifyDesktopKeyring {
    const SERVICE: &'static str = "CodexifyDesktopKeyring";
    const USERNAME: &'static str = "device_key";

    /// Store a 32‑byte key.
    pub fn store_key(key: &[u8]) -> Result<(), Box<dyn Error>> {
        if key.len() != 32 {
            return Err("Key must be 32 bytes".into());
        }
        let encoded = base64::encode(key);
        let kr = Keyring::new(Self::SERVICE, Self::USERNAME);
        kr.set_password(&encoded)?;
        Ok(())
    }

    /// Retrieve the stored key.
    pub fn retrieve_key() -> Result<Vec<u8>, Box<dyn Error>> {
        let kr = Keyring::new(Self::SERVICE, Self::USERNAME);
        let encoded = kr.get_password()?;
        let decoded = base64::decode(&encoded)?;
        if decoded.len() != 32 {
            return Err("Stored key is not 32 bytes".into());
        }
        Ok(decoded)
    }

    /// Delete the stored key.
    pub fn delete_key() -> Result<(), Box<dyn Error>> {
        let kr = Keyring::new(Self::SERVICE, Self::USERNAME);
        kr.delete_password()?;
        Ok(())
    }
}
