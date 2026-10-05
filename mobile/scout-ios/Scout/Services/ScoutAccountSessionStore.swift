import Foundation
import CryptoKit
import Security

struct ScoutAccountSession: Codable {
    let token: String
    let userID: String
    let expiresAt: Date
    let profileID: UUID
    let origin: String

    func validate(for profile: ScoutEndpointProfile, now: Date = Date()) throws {
        guard profileID == profile.id, origin == (try ScoutAccessOAuth.origin(for: profile)) else {
            throw ScoutRequestAuthenticationError.wrongConnection
        }
        guard !token.isEmpty, !userID.isEmpty,
              token.allSatisfy({ $0.isASCII && $0.asciiValue! >= 33 && $0.asciiValue! <= 126 }) else {
            throw ScoutRequestAuthenticationError.invalidSession
        }
        guard expiresAt > now else { throw ScoutRequestAuthenticationError.expiredSession }
    }
}

struct ScoutAccountSessionStore {
    private let service = "ai.resonantconstructs.codexify.scout.account-session"

    private func invalidateClientViews() {
        let key = "scout.accountSessionGeneration"
        UserDefaults.standard.set(UserDefaults.standard.integer(forKey: key) + 1, forKey: key)
    }

    private func query(_ profile: ScoutEndpointProfile) throws -> [String: Any] {
        guard profile.authenticationMode == .remoteSession else { throw ScoutRequestAuthenticationError.wrongConnection }
        let scope = profile.id.uuidString + "|" + (try ScoutAccessOAuth.origin(for: profile))
        return [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                kSecAttrAccount as String: ScoutAccessOAuth.base64URL(Data(SHA256.hash(data: Data(scope.utf8))))]
    }

    func save(_ session: ScoutAccountSession, for profile: ScoutEndpointProfile) throws {
        try session.validate(for: profile)
        let match = try query(profile)
        let data = try JSONEncoder().encode(session)
        let status = SecItemUpdate(match as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecSuccess { invalidateClientViews(); return }
        guard status == errSecItemNotFound else { throw ScoutKeychainError.saveFailed(status: status) }
        var insert = match
        insert[kSecValueData as String] = data
        insert[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        insert[kSecAttrSynchronizable as String] = false
        let added = SecItemAdd(insert as CFDictionary, nil)
        guard added == errSecSuccess else { throw ScoutKeychainError.saveFailed(status: added) }
        invalidateClientViews()
    }

    func load(for profile: ScoutEndpointProfile) throws -> ScoutAccountSession? {
        var match = try query(profile)
        match[kSecReturnData as String] = true
        match[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        let status = SecItemCopyMatching(match as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw ScoutKeychainError.loadFailed(status: status) }
        return try JSONDecoder().decode(ScoutAccountSession.self, from: data)
    }

    func delete(for profile: ScoutEndpointProfile) throws {
        let status = SecItemDelete(try query(profile) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw ScoutKeychainError.deleteFailed(status: status) }
        if status == errSecSuccess { invalidateClientViews() }
    }
}

extension URLSession {
    static let scoutAuthenticated: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.httpShouldSetCookies = false
        config.httpCookieStorage = nil
        config.urlCredentialStorage = nil
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: config, delegate: ScoutAuthNoRedirect(), delegateQueue: nil)
    }()
}
