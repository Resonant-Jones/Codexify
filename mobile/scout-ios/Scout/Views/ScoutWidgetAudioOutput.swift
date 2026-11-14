import AVFoundation
import Darwin
import Foundation

/// A widget-scoped output device for short, already rendered PCM clips.
/// The caller must arm playback through trusted UI before forwarding clips.
@MainActor
final class ScoutWidgetAudioOutput {
    private static let sampleRate = 24_000.0
    private static let maximumEncodedBytes = 192_000
    private static let maximumPCMBytes = 144_000
    private static let maximumVoices = 16
    private static let testClip: UInt32 = 0
    private static let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 1)!

    private enum PlaybackError: Error { case closed, noOutput }

    private struct Voice {
        let player: AVAudioPlayerNode
        let generation: UUID
    }

    private var engine: AVAudioEngine?
    private var players: [AVAudioPlayerNode] = []
    private let testPlayer = AVAudioPlayerNode()
    var onPlaybackFailure: ((Error) -> Void)?
    private var voices: [UInt32: Voice] = [:]
    private var isClosed = false

    // Bound work before decoding, including malformed messages. The bursts
    // allow overlapping short samples but prevent a page flooding the engine.
    private var encodedBytesAvailable = 384_000.0
    private var messagesAvailable = 24.0
    private var lastRefill = ProcessInfo.processInfo.systemUptime

    #if os(iOS)
    private var hasSessionLease = false
    #endif

    /// Activate the route before creating the graph, at the user's explicit
    /// Enable Sound action. Connections remain fixed while notes are playing.
    func prepare() throws {
        guard !isClosed else { throw PlaybackError.closed }
        guard engine?.isRunning != true else { return }
        do {
            #if os(iOS)
            if !hasSessionLease {
                try Self.acquireSession()
                hasSessionLease = true
            }
            #endif
            let engine = engine ?? AVAudioEngine()
            self.engine = engine
            #if os(iOS)
            let output = engine.outputNode.outputFormat(forBus: 0)
            guard output.channelCount > 0, output.sampleRate > 0 else { throw PlaybackError.noOutput }
            #endif
            if players.isEmpty {
                players = (0..<Self.maximumVoices).map { _ in AVAudioPlayerNode() }
                for player in players + [testPlayer] {
                    engine.attach(player)
                    engine.connect(player, to: engine.mainMixerNode, format: Self.format)
                }
            }
            engine.prepare()
            try engine.start()
        } catch {
            resetGraph()
            releaseSession()
            throw error
        }
    }

    /// A trusted, local test sound through the same graph used by widget clips.
    func playTestTone() throws {
        try prepare()
        let count = AVAudioFrameCount(Self.sampleRate * 0.22)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: Self.format, frameCapacity: count),
              let samples = buffer.floatChannelData?[0] else { throw PlaybackError.noOutput }
        buffer.frameLength = count
        for index in 0..<Int(count) {
            let time = Double(index) / Self.sampleRate
            let envelope = min(1, time / 0.01, (0.22 - time) / 0.03)
            samples[index] = Float(0.35 * envelope * sin(2 * .pi * 440 * time))
        }
        removeVoice(Self.testClip)
        schedule(testPlayer, clip: Self.testClip, buffer: buffer, delay: 0)
    }

    func play(clip: UInt32, pcm: String, delay: Double) {
        let voiceCount = voices.count - (voices[Self.testClip] == nil ? 0 : 1)
        guard !isClosed, clip != Self.testClip, voices[clip] == nil, voiceCount < Self.maximumVoices,
              delay.isFinite, (0...2).contains(delay), consumeMessageBudget() else { return }
        let encodedBytes = pcm.utf8.count
        guard encodedBytes > 0, encodedBytes <= Self.maximumEncodedBytes,
              encodedBytes % 4 == 0, encodedBytesAvailable >= Double(encodedBytes) else { return }
        encodedBytesAvailable -= Double(encodedBytes)
        guard let bytes = Data(base64Encoded: pcm), !bytes.isEmpty,
              bytes.count <= Self.maximumPCMBytes, bytes.count % 2 == 0,
              let buffer = AVAudioPCMBuffer(pcmFormat: Self.format, frameCapacity: AVAudioFrameCount(bytes.count / 2)),
              let samples = buffer.floatChannelData?[0] else { return }

        buffer.frameLength = buffer.frameCapacity
        bytes.withUnsafeBytes { source in
            for frame in 0..<Int(buffer.frameLength) {
                let sample = source.loadUnaligned(fromByteOffset: frame * 2, as: Int16.self)
                samples[frame] = Float(Int16(littleEndian: sample)) / 32_768
            }
        }

        do {
            try prepare()
        } catch {
            onPlaybackFailure?(error)
            return
        }
        guard let player = players.first(where: { player in
            !voices.values.contains { $0.player === player }
        }) else { return }
        schedule(player, clip: clip, buffer: buffer, delay: delay)
    }

    private func schedule(_ player: AVAudioPlayerNode, clip: UInt32, buffer: AVAudioPCMBuffer, delay: Double) {
        let generation = UUID()
        voices[clip] = Voice(player: player, generation: generation)
        updateVoiceVolumes()
        player.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.voices[clip]?.generation == generation else { return }
                self.removeVoice(clip)
            }
        }
        let when = delay > 0
            ? AVAudioTime(hostTime: mach_absolute_time() + AVAudioTime.hostTime(forSeconds: delay))
            : nil
        player.play(at: when)
    }

    func stop(clip: UInt32) {
        guard clip != Self.testClip else { return }
        removeVoice(clip)
    }

    func close() {
        guard !isClosed else { return }
        isClosed = true
        resetGraph()
        releaseSession()
    }

    private func resetGraph() {
        for voice in voices.values { voice.player.stop() }
        voices.removeAll()
        if let engine {
            engine.stop()
            for player in players + [testPlayer] where engine.attachedNodes.contains(player) {
                engine.detach(player)
            }
        }
        players.removeAll()
        engine = nil
    }

    private func removeVoice(_ clip: UInt32) {
        guard let voice = voices.removeValue(forKey: clip) else { return }
        voice.player.stop()
        updateVoiceVolumes()
    }

    private func updateVoiceVolumes() {
        // Even perfectly correlated full-scale samples stay within the local
        // widget's output ceiling when several clips overlap.
        let gain: Float = 0.6 / Float(max(1, voices.count))
        for voice in voices.values {
            voice.player.volume = gain
        }
    }

    private func consumeMessageBudget() -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        let elapsed = max(0, now - lastRefill)
        lastRefill = now
        encodedBytesAvailable = min(384_000, encodedBytesAvailable + elapsed * 384_000)
        messagesAvailable = min(24, messagesAvailable + elapsed * 48)
        guard messagesAvailable >= 1 else { return false }
        messagesAvailable -= 1
        return true
    }

    #if os(iOS)
    private struct SessionSettings {
        let category: AVAudioSession.Category
        let mode: AVAudioSession.Mode
        let options: AVAudioSession.CategoryOptions

        init(_ session: AVAudioSession) {
            category = session.category
            mode = session.mode
            options = session.categoryOptions
        }

        func apply(to session: AVAudioSession) throws {
            try session.setCategory(category, mode: mode, options: options)
        }
    }

    private static var sessionUsers = 0
    private static var previousSessionSettings: SessionSettings?

    private static func acquireSession() throws {
        if sessionUsers == 0 {
            let session = AVAudioSession.sharedInstance()
            let previous = SessionSettings(session)
            // The session is app-wide. If another feature already configured
            // it, use that setting instead of taking over the device route.
            let changesCategory = previous.category == .soloAmbient || previous.category == .ambient
            if changesCategory {
                try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            }
            do {
                try session.setActive(true)
            } catch {
                if changesCategory { try? previous.apply(to: session) }
                throw error
            }
            if changesCategory { previousSessionSettings = previous }
        }
        sessionUsers += 1
    }
    #endif

    private func releaseSession() {
        #if os(iOS)
        guard hasSessionLease else { return }
        hasSessionLease = false
        Self.sessionUsers -= 1
        guard Self.sessionUsers == 0, let previous = Self.previousSessionSettings else { return }
        Self.previousSessionSettings = nil
        let session = AVAudioSession.sharedInstance()
        guard session.category == .playback, session.mode == .default,
              session.categoryOptions == [.mixWithOthers] else { return }
        try? session.setActive(false, options: [.notifyOthersOnDeactivation])
        try? previous.apply(to: session)
        #endif
    }
}
