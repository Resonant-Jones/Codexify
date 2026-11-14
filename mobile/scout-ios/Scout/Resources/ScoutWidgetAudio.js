// Local playback subset for Scout's sandbox. This runs only inside the
// opaque widget frame. It renders PCM and has no access to the native app.
function installScoutWidgetAudio(session) {
    "use strict";

    const sampleRate = 24000;
    const maxSamples = sampleRate * 3;
    const maxBufferedSamples = sampleRate * 3;
    const maxVoices = 16;
    const maxPendingContexts = 8;
    const maxGraphNodes = 16;
    const sustainSeconds = 0.35;
    const lookAhead = 0.10;
    const chunkSeconds = 0.20;
    const destination = "destination";
    const now = () => performance.now() / 1000;
    let elapsed = 0;
    let enabledAt = 0;
    let enableGeneration = 0;
    const clock = () => elapsed + (enabled ? now() - enabledAt : 0);
    let nextClip = 0;
    let activeVoices = 0;
    let enabled = false;
    let unsupportedReported = false;
    const pendingContexts = new Set();
    const playingContexts = new Set();
    let recentFrames = 0;
    let frameWindow = now();

    // The native control is authoritative for output. The wrapper signals its
    // state to start/resume local synthesis without relying on a second tap.
    window.addEventListener("message", event => {
        const data = event.data;
        if (event.source !== window.parent || !data || data.channel !== "cfy-widget-audio-control" ||
            data.session !== session || typeof data.enabled !== "boolean" || enabled === data.enabled) return;
        if (data.enabled) {
            enabledAt = now();
            enableGeneration++;
            enabled = true;
            for (const context of Array.from(pendingContexts)) context.resume();
        } else {
            elapsed = clock();
            enabled = false;
            for (const context of Array.from(playingContexts)) context.pauseForMute();
        }
    });

    function send(action, fields = {}) {
        window.parent.postMessage({ channel: "cfy-widget-audio", session, action, ...fields }, "*");
    }

    function unsupportedAudio() {
        if (!unsupportedReported) {
            unsupportedReported = true;
            send("status", { code: "unsupported_audio" });
        }
        return new DOMException("This widget uses an unsupported audio feature.", "NotSupportedError");
    }

    function bounded(value, fallback, min, max) {
        const n = Number(value);
        return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
    }

    function toTime(value, fallback) {
        return bounded(value, fallback, 0, Number.MAX_SAFE_INTEGER);
    }

    class Param {
        constructor(context, value) {
            this.context = context;
            this.value = value;
            this.events = [];
        }

        record(kind, value, time, constant) {
            value = Number(value);
            time = Number(time);
            if (!Number.isFinite(value) || !Number.isFinite(time) || time < 0 || this.events.length >= 64) return this;
            // An initial ramp begins when scheduled, even when this context
            // has been open for a long time.
            if (!this.events.length && (kind === "linear" || kind === "exponential")) {
                this.events.push({ kind: "set", value: this.value, time: Math.min(time, this.context.currentTime) });
            }
            const event = { kind, value, time, constant };
            const i = this.events.findIndex(item => item.time > time);
            if (i < 0) this.events.push(event);
            else this.events.splice(i, 0, event);
            return this;
        }

        setValueAtTime(value, time) { return this.record("set", value, time); }
        linearRampToValueAtTime(value, time) { return this.record("linear", value, time); }
        exponentialRampToValueAtTime(value, time) { return this.record("exponential", value, time); }
        setTargetAtTime(value, time, constant) {
            return this.record("target", value, time, bounded(constant, 0.01, 0.00001, 60));
        }

        cancelScheduledValues(time) {
            this.events = this.events.filter(event => event.time < time);
            return this;
        }

        cancelAndHoldAtTime(time) {
            const value = this.valueAt(time);
            this.cancelScheduledValues(time);
            return this.setValueAtTime(value, time);
        }

        valueAt(time) {
            let value = Number.isFinite(this.value) ? this.value : 0;
            let previousTime = 0;
            let target;
            for (const event of this.events) {
                if (time < event.time) {
                    if (event.kind === "linear" || event.kind === "exponential") {
                        const part = (time - previousTime) / Math.max(0.000001, event.time - previousTime);
                        return event.kind === "exponential" && value > 0 && event.value > 0
                            ? value * (event.value / value) ** part
                            : value + part * (event.value - value);
                    }
                    break;
                }
                if (target) {
                    value = target.value + (value - target.value) * Math.exp(-(event.time - previousTime) / target.constant);
                }
                previousTime = event.time;
                target = event.kind === "target" ? event : undefined;
                if (!target) value = event.value;
            }
            return target
                ? target.value + (value - target.value) * Math.exp(-(time - previousTime) / target.constant)
                : value;
        }
    }

    class AudioNode {
        constructor(context, kind) {
            this.context = context;
            this.kind = kind;
            this.outputs = new Set();
        }

        connect(node) {
            if (!(node instanceof AudioNode) || node.context !== this.context) throw unsupportedAudio();
            if (this.outputs.size >= maxGraphNodes && !this.outputs.has(node)) throw unsupportedAudio();
            this.outputs.add(node);
            return node;
        }

        disconnect(node) {
            if (node) this.outputs.delete(node);
            else this.outputs.clear();
        }
    }

    class GainNode extends AudioNode {
        constructor(context) {
            super(context, "gain");
            this.gain = new Param(context, 1);
        }
    }

    class FilterNode extends AudioNode {
        constructor(context) {
            super(context, "filter");
            this.type = "lowpass";
            this.frequency = new Param(context, 350);
            this.Q = new Param(context, 1);
            this.gain = new Param(context, 0);
            this.detune = new Param(context, 0);
        }
    }

    class AnalyserNode extends AudioNode {
        constructor(context) {
            super(context, "analyser");
            this.fftSize = 2048;
            this.minDecibels = -100;
            this.maxDecibels = -30;
            this.smoothingTimeConstant = 0.8;
        }

        get fftSize() { return this.data.length; }
        set fftSize(size) {
            if (!Number.isInteger(size) || size < 32 || size > 2048 || (size & (size - 1))) {
                throw unsupportedAudio();
            }
            this.data = new Float32Array(size);
            this.cursor = 0;
            this.changed = true;
            this.magnitudes = null;
        }

        get frequencyBinCount() { return this.fftSize / 2; }

        record(value) {
            this.data[this.cursor] = value;
            this.cursor = (this.cursor + 1) % this.fftSize;
            this.changed = true;
        }

        getFloatTimeDomainData(destination) {
            for (let i = 0; i < Math.min(destination.length, this.fftSize); i++) {
                destination[i] = this.data[(this.cursor + i) % this.fftSize];
            }
        }

        getByteTimeDomainData(destination) {
            for (let i = 0; i < Math.min(destination.length, this.fftSize); i++) {
                destination[i] = bounded(128 * (1 + this.data[(this.cursor + i) % this.fftSize]), 128, 0, 255);
            }
        }

        spectrum() {
            if (!this.changed && this.magnitudes) return this.magnitudes;
            const size = this.fftSize;
            const real = new Float64Array(size);
            const imaginary = new Float64Array(size);
            for (let i = 0, reversed = 0; i < size; i++) {
                // Window the waveform before transforming the latest snapshot.
                const phase = 2 * Math.PI * i / size;
                const window = 0.42 - 0.5 * Math.cos(phase) + 0.08 * Math.cos(2 * phase);
                real[reversed] = this.data[(this.cursor + i) % size] * window;
                let bit = size >> 1;
                while (bit && (reversed & bit)) {
                    reversed ^= bit;
                    bit >>= 1;
                }
                reversed ^= bit;
            }
            for (let width = 2; width <= size; width *= 2) {
                const half = width / 2;
                for (let offset = 0; offset < half; offset++) {
                    const phase = -2 * Math.PI * offset / width;
                    const cosine = Math.cos(phase);
                    const sine = Math.sin(phase);
                    for (let i = offset; i < size; i += width) {
                        const upper = i + half;
                        const r = real[upper] * cosine - imaginary[upper] * sine;
                        const j = real[upper] * sine + imaginary[upper] * cosine;
                        real[upper] = real[i] - r;
                        imaginary[upper] = imaginary[i] - j;
                        real[i] += r;
                        imaginary[i] += j;
                    }
                }
            }
            const smoothing = this.magnitudes ? bounded(this.smoothingTimeConstant, 0.8, 0, 1) : 0;
            if (!this.magnitudes) this.magnitudes = new Float64Array(this.frequencyBinCount);
            for (let i = 0; i < this.frequencyBinCount; i++) {
                const magnitude = Math.hypot(real[i], imaginary[i]) / size;
                this.magnitudes[i] = smoothing * this.magnitudes[i] + (1 - smoothing) * magnitude;
            }
            this.changed = false;
            return this.magnitudes;
        }

        getFloatFrequencyData(destination) {
            const spectrum = this.spectrum();
            for (let i = 0; i < Math.min(destination.length, spectrum.length); i++) {
                destination[i] = 20 * Math.log10(spectrum[i]);
            }
        }

        getByteFrequencyData(destination) {
            const spectrum = this.spectrum();
            const range = Math.max(1, this.maxDecibels - this.minDecibels);
            for (let i = 0; i < Math.min(destination.length, spectrum.length); i++) {
                destination[i] = bounded(255 * (20 * Math.log10(spectrum[i]) - this.minDecibels) / range, 0, 0, 255);
            }
        }
    }

    class AudioBuffer {
        constructor(channels, length, rate) {
            this.numberOfChannels = bounded(channels, 1, 1, 2) | 0;
            this.length = bounded(length, 1, 1, maxBufferedSamples) | 0;
            this.sampleRate = bounded(rate, sampleRate, 8000, 96000);
            this.duration = this.length / this.sampleRate;
            this.channels = Array.from({ length: this.numberOfChannels }, () => new Float32Array(this.length));
        }

        getChannelData(channel) {
            if (!Number.isInteger(channel) || channel < 0 || channel >= this.numberOfChannels) {
                throw new RangeError("Audio channel is unavailable.");
            }
            return this.channels[channel];
        }

        copyToChannel(data, channel, offset = 0) {
            if (!Number.isInteger(offset) || offset < 0 || offset >= this.length) return;
            this.getChannelData(channel).set(data.subarray(0, this.length - offset), offset);
        }
    }

    class SourceNode extends AudioNode {
        constructor(context, kind) {
            super(context, kind);
            this.end = Infinity;
            this.clips = [];
            this.onended = null;
            this.phase = 0;
            this.position = 0;
            this.filters = new Map();
        }

        start(when = 0, offset = 0, duration) {
            if (this.startTime !== undefined || this.context.state === "closed" || activeVoices >= maxVoices) return;
            const start = Math.max(this.context.currentTime, toTime(when, 0));
            if (start - this.context.currentTime > 2) return;
            if (!enabled && !this.context.explicitlySuspended && !this.context.queueResume()) return;
            if (enabled && this.context.state === "suspended" && !this.context.explicitlySuspended) {
                this.context.startRunning();
            }
            this.startTime = start;
            this.cursor = start;
            this.position = bounded(offset, 0, 0, 3) * (this.buffer?.sampleRate ?? sampleRate);
            if (duration !== undefined) this.end = this.startTime + bounded(duration, 0, 0, 3);
            activeVoices += 1;
            this.context.sources.add(this);
            if (this.context.state === "running") {
                playingContexts.add(this.context);
                this.begin();
            }
        }

        begin() {
            this.timer = setTimeout(() => this.render(), 0);
        }

        stop(when = 0) {
            this.end = Math.max(this.context.currentTime, toTime(when, 0));
            if (this.startTime === undefined) return;
            const currentTime = this.context.currentTime;
            // A release can arrive after PCM has already been sent. Stop only
            // the affected voice and leave other notes in the sheet alone.
            if (this.end <= currentTime + 0.003) {
                this.finish(true);
            } else if (this.sent && this.end < this.cursor) {
                clearTimeout(this.stopTimer);
                this.stopTimer = setTimeout(() => this.finish(true), (this.end - currentTime) * 1000);
            }
        }

        finish(cancelAudio) {
            if (!this.context.sources.delete(this)) return;
            activeVoices -= 1;
            if (!this.context.sources.size) playingContexts.delete(this.context);
            clearTimeout(this.timer);
            clearTimeout(this.stopTimer);
            if (cancelAudio) {
                for (const item of this.clips) send("stop", { clip: item.clip });
            }
            this.clips.length = 0;
            if (typeof this.onended === "function") this.onended();
        }

        render() {
            const currentTime = this.context.currentTime;
            if (this.end <= currentTime || this.context.state !== "running") {
                this.finish(true);
                return;
            }
            if (this.cursor > currentTime + 0.20) {
                this.timer = setTimeout(() => this.render(), (this.cursor - currentTime - lookAhead) * 1000);
                return;
            }
            const graph = outputGraph(this);
            if (!graph) {
                this.finish(true);
                return;
            }

            // Render complete short percussion hits once; held notes get
            // short chunks so keyboard release and envelopes stay responsive.
            const finiteDuration = Number.isFinite(this.end) ? this.end - this.startTime : Infinity;
            const remaining = this.end - this.cursor;
            const desired = !this.sent && finiteDuration <= 1.5 ? remaining : (this.sent ? chunkSeconds : sustainSeconds);
            const count = Math.min(maxSamples, Math.ceil(Math.min(remaining, desired) * sampleRate));
            if (count <= 0) {
                this.timer = setTimeout(() => this.finish(false), Math.max(0, (this.end - currentTime) * 1000));
                return;
            }

            const newWindow = now();
            if (newWindow - frameWindow >= 1) {
                frameWindow = newWindow;
                recentFrames = 0;
            }
            if (recentFrames + count > sampleRate * 6 || nextClip >= 0xffffffff) {
                this.finish(true);
                return;
            }
            recentFrames += count;

            const bytes = new Uint8Array(count * 2);
            let produced = 0;
            let peak = 0;
            while (produced < count) {
                const time = this.cursor + produced / sampleRate;
                let value = this.sample(time);
                if (value === undefined) break;
                value = graph.sample(this.filters, value, time, produced);
                const signed = (bounded(value, 0, -1, 1) * 32767) | 0;
                peak |= Math.abs(signed);
                bytes[produced * 2] = signed & 0xff;
                bytes[produced * 2 + 1] = (signed >> 8) & 0xff;
                produced += 1;
            }

            if (produced && peak) {
                const clip = ++nextClip;
                const delay = bounded(this.cursor - this.context.currentTime, 0, 0, 2);
                this.clips = this.clips.filter(item => item.end > currentTime);
                this.clips.push({ clip, end: this.cursor + produced / sampleRate + 0.15 });
                send("play", { clip, delay, pcm: encode(bytes, produced * 2) });
            }

            this.sent = true;
            this.cursor += produced / sampleRate;
            if (produced < count || this.cursor >= this.end) {
                this.timer = setTimeout(() => this.finish(false), Math.max(0, (this.cursor - currentTime) * 1000));
            } else {
                this.timer = setTimeout(() => this.render(), Math.max(0, (this.cursor - currentTime - lookAhead) * 1000));
            }
        }
    }

    class OscillatorNode extends SourceNode {
        constructor(context) {
            super(context, "oscillator");
            this.type = "sine";
            this.frequency = new Param(context, 440);
            this.detune = new Param(context, 0);
        }

        sample(time) {
            const phase = this.phase;
            const frequency = bounded(this.frequency.valueAt(time) * 2 ** (this.detune.valueAt(time) / 1200), 0, 0, sampleRate / 2);
            this.phase = (phase + frequency / sampleRate) % 1;
            switch (this.type) {
            case "square": return phase < 0.5 ? 1 : -1;
            case "sawtooth": return 2 * phase - 1;
            case "triangle": return 1 - 4 * Math.abs(phase - 0.5);
            default: return Math.sin(2 * Math.PI * phase);
            }
        }
    }

    class BufferSourceNode extends SourceNode {
        constructor(context) {
            super(context, "buffer");
            this.buffer = null;
            this.loop = false;
            this.loopStart = 0;
            this.loopEnd = 0;
            this.playbackRate = new Param(context, 1);
            this.detune = new Param(context, 0);
        }

        sample(time) {
            if (!(this.buffer instanceof AudioBuffer)) return undefined;
            const data = this.buffer.getChannelData(0);
            const right = this.buffer.numberOfChannels === 2 ? this.buffer.getChannelData(1) : null;
            const loopStart = Math.max(0, Math.min(data.length - 1, this.loopStart * this.buffer.sampleRate)) | 0;
            const loopEnd = Math.max(loopStart + 1, Math.min(data.length, this.loopEnd * this.buffer.sampleRate || data.length)) | 0;
            if (this.loop && this.position >= loopEnd) this.position = loopStart + (this.position - loopStart) % (loopEnd - loopStart);
            if (this.position >= data.length) return undefined;
            const position = this.position | 0;
            const fraction = this.position - position;
            const channelSample = channel => {
                const next = channel[position + 1] ?? channel[position];
                return channel[position] + (next - channel[position]) * fraction;
            };
            const rate = bounded(this.playbackRate.valueAt(time) * 2 ** (this.detune.valueAt(time) / 1200), 1, 0, 16);
            this.position += rate * this.buffer.sampleRate / sampleRate;
            const left = channelSample(data);
            return right ? (left + channelSample(right)) * 0.5 : left;
        }
    }

    function outputGraph(source) {
        const nodes = [];
        const visiting = new Set();
        const visited = new Set();
        function visit(node) {
            if (visited.has(node)) return true;
            if (visiting.has(node) || visiting.size + visited.size >= maxGraphNodes) return false;
            visiting.add(node);
            for (const output of node.outputs) {
                if (!visit(output)) return false;
            }
            visiting.delete(node);
            visited.add(node);
            nodes.push(node);
            return true;
        }
        if (!source.outputs.size) return undefined;
        if (!visit(source)) {
            unsupportedAudio();
            return undefined;
        }
        nodes.reverse();
        const indexes = new Map(nodes.map((node, index) => [node, index]));
        const routes = nodes.map(node => Array.from(node.outputs, output => indexes.get(output)));
        const samples = new Float64Array(nodes.length);
        return {
            sample(filters, value, time, frame) {
                samples.fill(0);
                samples[0] = value;
                let result = 0;
                for (let i = 0; i < nodes.length; i++) {
                    const node = nodes[i];
                    let output = samples[i];
                    if (node.kind === "gain") output *= bounded(node.gain.valueAt(time), 0, -8, 8);
                    else if (node.kind === "filter") output = filterSample(node, filters, output, time, frame);
                    else if (node.kind === "analyser") node.record(output);
                    else if (node.kind === destination) result += output;
                    for (const downstream of routes[i]) samples[downstream] += output;
                }
                return result;
            }
        };
    }

    function filterSample(node, states, input, time, index) {
        let state = states.get(node);
        if (!state) {
            state = { x1: 0, x2: 0, y1: 0, y2: 0 };
            states.set(node, state);
        }
        if (index % 32 === 0) {
            const frequency = bounded(node.frequency.valueAt(time) * 2 ** (node.detune.valueAt(time) / 1200), 350, 1, sampleRate * 0.49);
            const angular = 2 * Math.PI * frequency / sampleRate;
            const cosine = Math.cos(angular);
            const alpha = Math.sin(angular) / (2 * bounded(node.Q.valueAt(time), 1, 0.1, 25));
            const a0 = 1 + alpha;
            state.a1 = -2 * cosine / a0;
            state.a2 = (1 - alpha) / a0;
            switch (node.type) {
            case "highpass":
                state.b0 = (1 + cosine) / (2 * a0);
                state.b1 = -2 * state.b0;
                state.b2 = state.b0;
                break;
            case "bandpass":
                state.b0 = alpha / a0;
                state.b1 = 0;
                state.b2 = -state.b0;
                break;
            default:
                state.b0 = (1 - cosine) / (2 * a0);
                state.b1 = 2 * state.b0;
                state.b2 = state.b0;
                break;
            }
        }
        const output = state.b0 * input + state.b1 * state.x1 + state.b2 * state.x2 - state.a1 * state.y1 - state.a2 * state.y2;
        state.x2 = state.x1;
        state.x1 = input;
        state.y2 = state.y1;
        state.y1 = output;
        return output;
    }

    function encode(bytes, length) {
        let binary = "";
        for (let offset = 0; offset < length; offset += 8192) {
            binary += String.fromCharCode(...bytes.subarray(offset, Math.min(length, offset + 8192)));
        }
        return btoa(binary);
    }

    class AudioContext {
        constructor() {
            this.sampleRate = sampleRate;
            this.running = enabled;
            this.generation = enableGeneration;
            this.closed = false;
            this.startedAt = clock();
            this.pausedAt = 0;
            this.resumeCallbacks = [];
            this.sources = new Set();
            this.destination = new AudioNode(this, destination);
            this.onstatechange = null;
            this.explicitlySuspended = false;
        }

        get state() {
            return this.closed ? "closed" : this.running && enabled && this.generation === enableGeneration
                ? "running" : "suspended";
        }

        get currentTime() { return this.running ? clock() - this.startedAt : this.pausedAt; }

        queueResume() {
            if (pendingContexts.has(this)) return true;
            if (pendingContexts.size >= maxPendingContexts) return false;
            pendingContexts.add(this);
            return true;
        }

        startRunning() {
            pendingContexts.delete(this);
            if (!this.running) this.startedAt = clock() - this.pausedAt;
            this.running = true;
            this.generation = enableGeneration;
            if (this.sources.size) playingContexts.add(this);
            for (const source of this.sources) source.begin();
            for (const callback of this.resumeCallbacks.splice(0)) callback.resolve();
            if (typeof this.onstatechange === "function") this.onstatechange();
        }

        resume() {
            if (this.state === "closed") return Promise.reject(new Error("Audio context is closed."));
            this.explicitlySuspended = false;
            if (enabled) {
                if (this.state !== "running") this.startRunning();
                return Promise.resolve();
            }
            if (this.resumeCallbacks.length >= 8 || !this.queueResume()) {
                return Promise.reject(new Error("Audio context is waiting for the sound control."));
            }
            return new Promise((resolve, reject) => this.resumeCallbacks.push({ resolve, reject }));
        }

        pauseForMute() {
            this.pausedAt = this.currentTime;
            this.running = false;
            // A note from an earlier enable cycle must not start again.
            for (const source of this.sources) source.finish(false);
            if (typeof this.onstatechange === "function") this.onstatechange();
        }

        suspend() {
            if (this.state === "closed") return Promise.reject(new Error("Audio context is closed."));
            this.pausedAt = this.currentTime;
            this.running = false;
            this.explicitlySuspended = true;
            pendingContexts.delete(this);
            for (const source of this.sources) source.finish(true);
            return Promise.resolve();
        }

        close() {
            this.pausedAt = this.currentTime;
            this.running = false;
            this.closed = true;
            pendingContexts.delete(this);
            for (const source of this.sources) source.finish(true);
            for (const callback of this.resumeCallbacks.splice(0)) callback.reject(new Error("Audio context is closed."));
            return Promise.resolve();
        }

        createOscillator() { return new OscillatorNode(this); }
        createGain() { return new GainNode(this); }
        createBiquadFilter() { return new FilterNode(this); }
        createBuffer(channels, length, rate) { return new AudioBuffer(channels, length, rate); }
        createBufferSource() { return new BufferSourceNode(this); }
        createAnalyser() { return new AnalyserNode(this); }
        createDynamicsCompressor() { throw unsupportedAudio(); }
        createDelay() { throw unsupportedAudio(); }
        createConvolver() { throw unsupportedAudio(); }
        createStereoPanner() { throw unsupportedAudio(); }
        decodeAudioData() { return Promise.reject(unsupportedAudio()); }
    }

    try {
        for (const name of ["AudioContext", "webkitAudioContext"]) {
            const original = Object.getOwnPropertyDescriptor(window, name);
            if (original && !original.configurable && original.writable) window[name] = AudioContext;
            else Object.defineProperty(window, name, { value: AudioContext });
        }
    } catch {
        unsupportedAudio();
        return;
    }
    send("ready");
}
