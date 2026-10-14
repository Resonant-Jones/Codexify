import AppIntents

struct ScoutAppShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: ListScoutThreadsIntent(),
            phrases: ["List threads in \(.applicationName)"],
            shortTitle: "List threads", systemImageName: "bubble.left.and.bubble.right")
        AppShortcut(intent: CreateScoutThreadIntent(),
            phrases: ["Create a thread in \(.applicationName)"],
            shortTitle: "Create thread", systemImageName: "plus.bubble")
    }
}
