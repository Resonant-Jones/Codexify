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
                "Services/ScoutEndpointConnectivityProbe.swift",
                "Services/ScoutKeychainStore.swift",
            ],
            linkerSettings: [
                .linkedFramework("Security")
            ]
        ),
    ]
)
// Tests are run via the standalone runner:
//   swiftc -o /tmp/scout_test_runner \
//     Scout/Models/ScoutEndpointProfile.swift \
//     Scout/Models/ScoutHealthSnapshot.swift \
//     Scout/Services/ScoutEndpointConnectivityProbe.swift \
//     Tests/Runner.swift \
//     -framework Security \
//     && /tmp/scout_test_runner
