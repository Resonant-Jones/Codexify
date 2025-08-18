#[cfg(target_os = "macos")]
mod macos {
    use security_framework::authentication::{self, AuthenticationContext};

    pub fn authenticate() -> Result<bool, String> {
        let ctx = AuthenticationContext::new()
            .map_err(|e| format!("Failed to create auth context: {}", e))?;
        ctx.evaluate_policy(authentication::Policy::DeviceOwnerAuthenticationWithBiometrics)
            .map(|_| true)
            .map_err(|e| format!("Biometric auth failed: {}", e))
    }
}

#[cfg(target_os = "windows")]
mod windows {
    // Placeholder for Windows Hello integration.
    // A real implementation would use the Windows Biometric Framework.
    pub fn authenticate() -> Result<bool, String> {
        // For demo purposes we simply return true.
        Ok(true)
    }
}

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
mod stub {
    pub fn authenticate() -> Result<bool, String> {
        Err("Biometric authentication not supported on this platform".into())
    }
}

#[cfg(target_os = "macos")]
pub fn authenticate() -> Result<bool, String> {
    macos::authenticate()
}

#[cfg(target_os = "windows")]
pub fn authenticate() -> Result<bool, String> {
    windows::authenticate()
}

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
pub fn authenticate() -> Result<bool, String> {
    stub::authenticate()
}
