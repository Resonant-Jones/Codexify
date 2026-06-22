// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "Scout",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "Scout", targets: ["Scout"]),
    ],
    targets: [
        .target(
            name: "Scout",
            path: "Scout",
            exclude: [
                "Views/",
                "ScoutApp.swift",
                "ContentView.swift",
            ],
            sources: [
                "Models/ScoutAppRoute.swift",
                "Models/ScoutEndpointProfile.swift",
                "Models/ScoutHealthSnapshot.swift",
                "Models/ScoutLLMHealthSnapshot.swift",
                "Models/ScoutLLMCatalogSnapshot.swift",
                "Models/ScoutChatThreadSummary.swift",
                "Models/ScoutChatMessageSummary.swift",
                "Models/ScoutThreadDocumentSummary.swift",
                "Models/ScoutDocumentDetail.swift",
                "Models/ScoutRAGTraceSnapshot.swift",
                "Models/ScoutTaskReceiptSummary.swift",
                "Services/ScoutEndpointConnectivityProbe.swift",
                "Services/ScoutLLMHealthProbe.swift",
                "Services/ScoutLLMCatalogProbe.swift",
                "Services/ScoutGuardianThreadsProbe.swift",
                "Services/ScoutGuardianThreadMessagesProbe.swift",
                "Services/ScoutGuardianSendMessageService.swift",
                "Services/ScoutGuardianCompleteThreadService.swift",
                "Services/ScoutTaskEventStreamService.swift",
                "Services/ScoutThreadDocumentsProbe.swift",
                "Services/ScoutDocumentDetailProbe.swift",
                "Services/ScoutRAGTraceProbe.swift",
                "Services/ScoutThreadTasksProbe.swift",
                "Services/ScoutMediaDocumentsProbe.swift",
                "Services/ScoutCreateThreadProbe.swift",
                "Services/ScoutRenameThreadProbe.swift",
                "Services/ScoutKeychainStore.swift",
            ],
            linkerSettings: [
                .linkedFramework("Security")
            ]
        ),
    ]
)

// Tests are run via the standalone test runner. XCTest and Swift Testing
// are unavailable on this system (Command Line Tools only, no Xcode).
//
// Build the library:
//   cd mobile/scout-ios && swift build
//
// Run tests:
//   swiftc -o /tmp/scout_test_runner \
//     Scout/Models/*.swift \
//     Scout/Services/*.swift \
//     Tests/Runner.swift \
//     -framework Security \
//     && /tmp/scout_test_runner
