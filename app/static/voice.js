/* Shared Realtime voice client used by both the training and agent pages.
 *
 * Connects the browser straight to the OpenAI Realtime API over WebSocket,
 * streams mic audio as PCM16, and plays the model's audio back.
 *
 * Two behaviours this file exists to get right:
 *   1. Barge-in: when the user starts talking over the AI, we immediately stop
 *      playback AND cancel the in-flight response. Without this the AI keeps
 *      talking over the user (the original bug).
 *   2. Backchannel: brief "mm-hm / yeah / okay" acknowledgements while the user
 *      speaks, produced locally via the browser SpeechSynthesis API so they are
 *      fully decoupled from the model's audio stream and reasoning.
 */
(function (global) {
  "use strict";

  const SAMPLE_RATE = 24000;
  const BACKCHANNELS = ["mm-hm", "yeah", "okay", "right", "uh-huh", "got it"];
  // Fire a backchannel only after the user has been talking this long, and no
  // more often than the throttle. Heuristic — tune to taste.
  const BACKCHANNEL_AFTER_MS = 2200;
  const BACKCHANNEL_THROTTLE_MS = 3500;

  function pcm16ToBase64(float32) {
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      int16[i] = Math.max(-32768, Math.min(32767, Math.floor(float32[i] * 32768)));
    }
    const bytes = new Uint8Array(int16.buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  function base64ToFloat32(b64) {
    const raw = atob(b64);
    const samples = new Int16Array(raw.length / 2);
    for (let i = 0; i < samples.length; i++) {
      samples[i] = raw.charCodeAt(i * 2) | (raw.charCodeAt(i * 2 + 1) << 8);
    }
    const f = new Float32Array(samples.length);
    for (let i = 0; i < samples.length; i++) f[i] = samples[i] / 32768;
    return f;
  }

  class VoiceSession {
    constructor(config, handlers) {
      this.config = config;                 // from /training/session or /agent/session
      this.on = handlers || {};             // { onStatus, onTranscript, onEnd }
      this.ws = null;
      this.micStream = null;
      this.micCtx = null;
      this.micProcessor = null;
      this.playbackCtx = null;
      this.scheduledSources = [];
      this.nextPlayTime = 0;
      this.aiSpeaking = false;
      this.transcript = [];
      this.active = false;
      this._backchannelTimer = null;
      this._lastBackchannel = 0;
    }

    _status(text) { if (this.on.onStatus) this.on.onStatus(text); }

    _emit(role, text) {
      this.transcript.push({ role, text, t: Date.now() });
      if (this.on.onTranscript) this.on.onTranscript(role, text);
    }

    async start() {
      this.active = true;
      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: SAMPLE_RATE, echoCancellation: true, noiseSuppression: true },
      });
      this.playbackCtx = new AudioContext({ sampleRate: SAMPLE_RATE });

      // Connect only to our own server, which relays to OpenAI (same origin, no key).
      const scheme = location.protocol === "https:" ? "wss://" : "ws://";
      const url = scheme + location.host + "/ws/realtime";
      this.ws = new WebSocket(url);

      this.ws.onopen = () => this._onOpen();
      this.ws.onmessage = (e) => this._onMessage(JSON.parse(e.data));
      this.ws.onerror = (e) => {
        console.error("Realtime WS error", e);
        this._status("Connection error (check DevTools console)");
      };
      this.ws.onclose = (e) => {
        console.warn("Realtime WS closed", e.code, e.reason);
        if (this.active) {
          this._status("Connection closed [code " + e.code +
            (e.reason ? ", " + e.reason : "") + "]");
        }
      };
    }

    _onOpen() {
      const greetsFirst = this.config.greeter === "user";
      const instructions = this.config.instructions +
        (greetsFirst
          ? "\n\nIMPORTANT: The other person speaks first. WAIT for them before responding. Do NOT speak first."
          : "");

      this.ws.send(JSON.stringify({
        type: "session.update",
        session: {
          type: "realtime",
          instructions,
          audio: {
            input: {
              format: { type: "audio/pcm", rate: SAMPLE_RATE },
              transcription: { model: "whisper-1" },
              // interrupt_response lets the server also stop generating when the
              // user barges in; we additionally stop playback locally for snappiness.
              turn_detection: {
                type: "server_vad",
                threshold: 0.8,
                prefix_padding_ms: 200,
                silence_duration_ms: 700,
                interrupt_response: true,
              },
            },
            output: {
              format: { type: "audio/pcm", rate: SAMPLE_RATE },
              voice: this.config.voice,
            },
          },
        },
      }));

      this._startMic();
      // If the AI greets first (agent mode), kick off its opening line.
      if (this.config.greeter === "ai") {
        this.ws.send(JSON.stringify({ type: "response.create" }));
      }
      this._status("Live");
    }

    _startMic() {
      this.micCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
      const src = this.micCtx.createMediaStreamSource(this.micStream);
      this.micProcessor = this.micCtx.createScriptProcessor(4096, 1, 1);
      src.connect(this.micProcessor);
      this.micProcessor.connect(this.micCtx.destination);
      this.micProcessor.onaudioprocess = (e) => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN || !this.active) return;
        this.ws.send(JSON.stringify({
          type: "input_audio_buffer.append",
          audio: pcm16ToBase64(e.inputBuffer.getChannelData(0)),
        }));
      };
    }

    _queueAudio(b64) {
      const f = base64ToFloat32(b64);
      const buffer = this.playbackCtx.createBuffer(1, f.length, SAMPLE_RATE);
      buffer.getChannelData(0).set(f);
      const source = this.playbackCtx.createBufferSource();
      source.buffer = buffer;
      source.connect(this.playbackCtx.destination);
      const now = this.playbackCtx.currentTime;
      const startAt = Math.max(now, this.nextPlayTime);
      source.start(startAt);
      this.nextPlayTime = startAt + buffer.duration;
      this.aiSpeaking = true;
      this.scheduledSources.push(source);
      source.onended = () => {
        this.scheduledSources = this.scheduledSources.filter((s) => s !== source);
        if (!this.scheduledSources.length) this.aiSpeaking = false;
      };
    }

    _stopPlayback() {
      // Barge-in: kill everything already scheduled so the AI goes silent at once.
      for (const s of this.scheduledSources) {
        try { s.stop(); } catch (_) { /* already stopped */ }
      }
      this.scheduledSources = [];
      this.nextPlayTime = this.playbackCtx ? this.playbackCtx.currentTime : 0;
      this.aiSpeaking = false;
    }

    _onMessage(msg) {
      switch (msg.type) {
        case "session.created":
          console.log("Realtime session.created");
          break;
        case "session.updated":
          console.log("Realtime session.updated");
          break;

        case "input_audio_buffer.speech_started":
          // User started talking. If the AI was mid-utterance, that's a barge-in:
          // stop local playback and cancel the server-side response.
          if (this.aiSpeaking) {
            this._stopPlayback();
            this.ws.send(JSON.stringify({ type: "response.cancel" }));
          }
          this._maybeStartBackchannel();
          break;

        case "input_audio_buffer.speech_stopped":
          this._stopBackchannel();
          break;

        case "response.audio.delta":
        case "response.output_audio.delta":
          if (msg.delta) this._queueAudio(msg.delta);
          break;

        case "response.audio_transcript.done":
        case "response.output_audio_transcript.done":
          if (msg.transcript) this._emit("ai", msg.transcript);
          break;

        case "conversation.item.input_audio_transcription.completed":
          if (msg.transcript) this._emit("user", msg.transcript);
          break;

        case "error":
          console.error("Realtime error event:", msg.error);
          this._status("Realtime error: " +
            (msg.error && (msg.error.message || msg.error.code) || "unknown"));
          break;
      }
    }

    /* ---- Backchannel (local, decoupled from the model) ------------------ */

    _maybeStartBackchannel() {
      if (!this.config.backchannel || !global.speechSynthesis) return;
      this._stopBackchannel();
      // Only after the user has been speaking a while, so we don't chirp at every
      // tiny sound. CEILING: local synth is a different voice than the model's,
      // and speaker output may bleed into the mic. Upgrade: server-side mixed
      // low-latency backchannel audio in the model voice + echo cancellation.
      this._backchannelTimer = setTimeout(() => {
        const now = Date.now();
        if (now - this._lastBackchannel < BACKCHANNEL_THROTTLE_MS) return;
        this._lastBackchannel = now;
        const u = new SpeechSynthesisUtterance(
          BACKCHANNELS[Math.floor(Math.random() * BACKCHANNELS.length)]
        );
        u.volume = 0.5; u.rate = 1.1; u.pitch = 1.0;
        global.speechSynthesis.speak(u);
      }, BACKCHANNEL_AFTER_MS);
    }

    _stopBackchannel() {
      if (this._backchannelTimer) {
        clearTimeout(this._backchannelTimer);
        this._backchannelTimer = null;
      }
    }

    stop() {
      this.active = false;
      this._stopBackchannel();
      this._stopPlayback();
      if (this.micProcessor) { this.micProcessor.disconnect(); this.micProcessor = null; }
      if (this.micCtx) { this.micCtx.close(); this.micCtx = null; }
      if (this.micStream) { this.micStream.getTracks().forEach((t) => t.stop()); this.micStream = null; }
      if (this.ws) { this.ws.close(); this.ws = null; }
      if (this.playbackCtx) { this.playbackCtx.close(); this.playbackCtx = null; }
      this._status("Ended");
      if (this.on.onEnd) this.on.onEnd(this.transcript);
      return this.transcript;
    }

    /** Flatten the transcript into "Role: text" lines for grading. */
    transcriptText() {
      const label = { user: "Agent", ai: "Customer" };
      return this.transcript.map((m) => (label[m.role] || m.role) + ": " + m.text).join("\n");
    }
  }

  global.VoiceSession = VoiceSession;
})(window);
