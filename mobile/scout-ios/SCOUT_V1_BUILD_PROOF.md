# Scout V1 Build Proof

## Scope

This document records the current build-surface classification of `mobile/scout-ios/` as of the Scout V1 capability baseline. It captures exact commands, results, and limitations of the current build toolchain.

## Current Build Surface

| Surface | Status | Notes |
|---|---|---|
| `Package.swift` | Present | Library target for models + services |
| `swift build` | ✅ Passes | Scout library compiles cleanly |
| `swift test` | ❌ No test target | XCTest unavailable; standalone runner used instead |
| Standalone test runner | ✅ 232 passed, 0 failed | `swiftc`-compiled `Tests/Runner.swift` with mock URLProtocol |
| `.xcodeproj` / `.xcworkspace` | ❌ Absent | No Xcode project exists |
| `xcodebuild` | ⚠️ Available but not applicable | No project to build |
| Simulator / device smoke | ❌ Not proven | No app target, no simulator run |

**Classification: Source / parse / test-runner proven, not app-target proven.**

## Evidence Commands

### 1. Swift version

```bash
swift --version
```

```
swift-driver version: 1.148.6 Apple Swift version 6.3.2
```

### 2. Package build

```bash
cd mobile/scout-ios && swift build
```

Result: **Build complete.** Library target `Scout` compiles all models and services.

### 3. Swift test

```bash
cd mobile/scout-ios && swift test
```

Result: **No tests found.** The `Package.swift` defines only a library target. XCTest and Swift Testing are unavailable on this system (Command Line Tools only, no Xcode XCTest framework in `swift test` path).

### 4. Standalone test runner

```bash
cd mobile/scout-ios && swiftc -o /tmp/scout_test_runner \
  Scout/Models/ScoutEndpointProfile.swift \
  ... (all model + service files) \
  Tests/Runner.swift \
  -framework Security \
  && /tmp/scout_test_runner
```

Result: **232 passed, 0 failed.**

### 5. Individual file parse check

```bash
swiftc -parse mobile/scout-ios/Scout/Views/GuardianChatView.swift
```

Result: **Passes.** All SwiftUI views parse cleanly.

### 6. xcodebuild

```bash
xcodebuild -version
```

```
Xcode 26.2.1
Build version 17C100
```

No `.xcodeproj` or `.xcworkspace` exists — `xcodebuild` cannot build an app target.

## Results

| Check | Result |
|---|---|
| `swift build` (library) | ✅ PASS |
| `swiftc -parse` (all files) | ✅ PASS |
| Standalone test runner | ✅ 232 passed, 0 failed |
| `swift test` (package) | ❌ No test target |
| `xcodebuild` (app) | ❌ No project |

## What This Proves

- The Scout Swift source compiles cleanly under Swift 6.3.2.
- All models and services form a valid Swift module.
- All 232 behavioral assertions pass via a standalone mock-URLProtocol test runner.
- Every view, model, and service file is syntactically valid Swift.

## What This Does Not Prove

- Scout does not have an Xcode project or app target — it cannot be built as an `.app` or run in the iOS simulator.
- The SwiftUI views are parse-clean but have not been rendered or interaction-tested.
- The standalone test runner uses `URLSession` mocking; no live Vault connectivity has been tested in CI.
- No device build, TestFlight, or App Store readiness is claimed.
- The Swift package test target does not work because XCTest is not available in the `swift test` path on this system (Command Line Tools only).

## Next Build-Seam Recommendation

To advance from source-proven to app-target-proven:

1. Add an Xcode project (`.xcodeproj`) with an iOS app target wrapping the existing Swift source.
2. Or add an iOS test target to `Package.swift` if XCTest becomes available via a full Xcode installation.
3. Once an app target exists, run `xcodebuild -scheme Scout -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 16' build` to confirm the app compiles.
4. Once a simulator build succeeds, add a UI smoke test that launches the app and verifies tab visibility.

These are future infrastructure tasks, not Scout feature tasks.
