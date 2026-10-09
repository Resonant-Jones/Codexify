import Foundation
import Security

struct ScoutAccessCredentialStore {
    private let service = "ai.resonantconstructs.codexify.scout.ingress"

    private func query(_ profile: ScoutEndpointProfile) throws -> [String: Any] {
        try ScoutAccessOAuth.requireHosted(profile)
        return [kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: service,
                kSecAttrAccount as String: try ScoutAccessOAuth.credentialAccount(for: profile)]
    }

    func save(_ credential: ScoutAccessOAuth.Credential, for profile: ScoutEndpointProfile) throws {
        let match = try query(profile)
        let data = try JSONEncoder().encode(credential)
        let update = SecItemUpdate(match as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if update == errSecSuccess { return }
        guard update == errSecItemNotFound else { throw ScoutKeychainError.saveFailed(status: update) }
        var insert = match
        insert[kSecValueData as String] = data
        insert[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        insert[kSecAttrSynchronizable as String] = false
        let status = SecItemAdd(insert as CFDictionary, nil)
        guard status == errSecSuccess else { throw ScoutKeychainError.saveFailed(status: status) }
    }

    func load(for profile: ScoutEndpointProfile) throws -> ScoutAccessOAuth.Credential? {
        var match = try query(profile)
        match[kSecReturnData as String] = true
        match[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        let status = SecItemCopyMatching(match as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else {
            throw ScoutKeychainError.loadFailed(status: status)
        }
        return try JSONDecoder().decode(ScoutAccessOAuth.Credential.self, from: data)
    }

    func delete(for profile: ScoutEndpointProfile) throws {
        let status = SecItemDelete(try query(profile) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw ScoutKeychainError.deleteFailed(status: status)
        }
    }
}
