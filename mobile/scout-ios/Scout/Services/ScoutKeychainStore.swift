import Foundation
import Security
import CryptoKit

enum ScoutKeychainError: Error {
    case saveFailed(status: OSStatus)
    case loadFailed(status: OSStatus)
    case deleteFailed(status: OSStatus)
}

struct ScoutKeychainStore {
    private let service = "com.codexify.scout"
    // The legacy global slot is intentionally never adopted by a new node.
    static func credentialAccount(for profile: ScoutEndpointProfile) throws -> String {
        let scope = profile.id.uuidString + "|" + (try ScoutAccessOAuth.origin(for: profile))
        return "node-api-key." + ScoutAccessOAuth.base64URL(Data(SHA256.hash(data: Data(scope.utf8))))
    }

    func saveAPIKey(_ key: String, for profile: ScoutEndpointProfile) throws {
        try deleteAPIKey(for: profile)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: try Self.credentialAccount(for: profile),
            kSecValueData as String: Data(key.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            kSecAttrSynchronizable as String: false
        ]

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw ScoutKeychainError.saveFailed(status: status)
        }
    }

    func loadAPIKey(for profile: ScoutEndpointProfile) throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: try Self.credentialAccount(for: profile),
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else {
            throw ScoutKeychainError.loadFailed(status: status)
        }

        return String(data: data, encoding: .utf8)
    }

    func deleteAPIKey(for profile: ScoutEndpointProfile) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: try Self.credentialAccount(for: profile)
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw ScoutKeychainError.deleteFailed(status: status)
        }
    }

    func hasAPIKey(for profile: ScoutEndpointProfile) -> Bool {
        (try? loadAPIKey(for: profile)) != nil
    }
}
