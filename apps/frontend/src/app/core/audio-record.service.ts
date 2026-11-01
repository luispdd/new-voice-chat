import { Injectable, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AudioPlaybackService } from './audio-playback.service';

@Injectable({
  providedIn: 'root',
})
export class AudioRecordService {
  private audioPlayback = inject(AudioPlaybackService);
  private api = inject(ApiService);

  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private analyser: AnalyserNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private gainNode: GainNode | null = null;

  private _isRecording = signal<boolean>(false);
  readonly isRecording = this._isRecording.asReadonly();

  private _audioLevel = signal<number>(0);
  readonly audioLevel = this._audioLevel.asReadonly();

  /** Incremented each time an utterance ends and `audio_end` has been sent to the backend. */
  private _utteranceEnded = signal<number>(0);
  readonly utteranceEnded = this._utteranceEnded.asReadonly();

  private _speechDetected = signal<number>(0);
  readonly speechDetected = this._speechDetected.asReadonly();

  private chunkCount = 0;
  private sampleRate = 16000;

  // Streaming: microphone audio is sent to the backend in ~100 ms PCM frames while the user speaks
  private pendingFrames: Float32Array[] = [];
  private pendingSamples = 0;

  // VAD parameters
  private vadActive = false;
  private silenceTimer: any = null;
  private readonly silenceThreshold = 0.018;
  private readonly bargeInThreshold = 0.045;
  private consecutiveSpeechFrames = 0;
  private lastUtteranceEndTime = 0;
  private readonly silenceDurationMs = 1500;
  // Pause hint: after this much silence the backend starts a speculative transcription
  private readonly pauseHintMs = 700;
  private pauseTimer: any = null;
  private pauseSent = false;

  get isRecordingActive(): boolean {
    return this._isRecording();
  }

  async startRecording(): Promise<void> {
    if (this._isRecording()) return;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000,
      });
      this.sampleRate = this.audioContext.sampleRate;

      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;

      this.gainNode = this.audioContext.createGain();
      this.gainNode.gain.value = 0; // Mute gain node to prevent mic input echoing to speakers

      this.chunkCount = 0;
      this.pendingFrames = [];
      this.pendingSamples = 0;
      this.vadActive = false;
      this._isRecording.set(true);

      const dataArray = new Uint8Array(new ArrayBuffer(this.analyser.frequencyBinCount));
      const preRollChunks: Float32Array[] = [];
      const maxPreRoll = 3; // Keep ~380ms of audio before speech onset to preserve initial consonants

      // Modern AudioWorkletNode processor
      const workletCode = `
        class AudioRecorderProcessor extends AudioWorkletProcessor {
          process(inputs) {
            const input = inputs[0];
            if (input && input[0] && input[0].length > 0) {
              this.port.postMessage(input[0]);
            }
            return true;
          }
        }
        registerProcessor('audio-recorder-processor', AudioRecorderProcessor);
      `;
      const blob = new Blob([workletCode], { type: 'application/javascript' });
      const workletUrl = URL.createObjectURL(blob);
      try {
        await this.audioContext.audioWorklet.addModule(workletUrl);
      } finally {
        URL.revokeObjectURL(workletUrl);
      }

      this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-recorder-processor');
      this.workletNode.port.onmessage = (e: MessageEvent<Float32Array>) => {
        this.processAudioChunk(e.data, dataArray, preRollChunks, maxPreRoll);
      };

      source.connect(this.analyser);
      this.analyser.connect(this.workletNode);
      this.workletNode.connect(this.gainNode);
      this.gainNode.connect(this.audioContext.destination);

    } catch (err) {
      console.error('Error starting audio recording:', err);
      this.stopRecording();
      throw err;
    }
  }

  private processAudioChunk(
    inputData: Float32Array,
    dataArray: Uint8Array<ArrayBuffer>,
    preRollChunks: Float32Array[],
    maxPreRoll: number
  ): void {
    if (!this._isRecording()) return;
    const chunk = new Float32Array(inputData);

    // Calculate RMS audio level
    this.analyser?.getByteFrequencyData(dataArray);
    let sum = 0;
    for (let i = 0; i < inputData.length; i++) {
      sum += inputData[i] * inputData[i];
    }
    const rms = Math.sqrt(sum / inputData.length);
    this._audioLevel.set(Math.min(rms * 5, 1)); // Normalized 0-1

    const now = Date.now();
    const isAssistantSpeaking = this.audioPlayback.isPlaying();
    const activeThreshold = isAssistantSpeaking ? this.bargeInThreshold : this.silenceThreshold;
    const inCooldown = now - this.lastUtteranceEndTime < 500;

    // Voice Activity Detection logic
    if (rms > activeThreshold && !inCooldown) {
      this.consecutiveSpeechFrames++;
      if (this.consecutiveSpeechFrames >= 2) {
        if (!this.vadActive) {
          this.vadActive = true;
          this._speechDetected.update((c) => c + 1);
          // Announce the utterance, then stream pre-roll chunks so initial consonants/phonemes are preserved
          this.api.sendWsMessage({ type: 'audio_start', sample_rate: this.sampleRate });
          this.pauseSent = false;
          this.chunkCount = 0;
          this.pendingFrames = [];
          this.pendingSamples = 0;
          for (const preRoll of preRollChunks) {
            this.queueFrame(preRoll);
          }
          preRollChunks.length = 0;
          this.queueFrame(chunk);
        } else {
          this.queueFrame(chunk);
        }

        if (this.silenceTimer) {
          clearTimeout(this.silenceTimer);
          this.silenceTimer = null;
        }
        this.clearPauseHint(true);
      }
    } else {
      this.consecutiveSpeechFrames = 0;
      if (this.vadActive) {
        this.queueFrame(chunk);
        if (!this.pauseTimer && !this.pauseSent) {
          this.pauseTimer = setTimeout(() => {
            this.pauseTimer = null;
            if (this.vadActive) {
              this.flushFrames();
              this.api.sendWsMessage({ type: 'audio_pause' });
              this.pauseSent = true;
            }
          }, this.pauseHintMs);
        }
        if (!this.silenceTimer) {
          this.silenceTimer = setTimeout(() => {
            if (this.vadActive && this.chunkCount > 5) {
              this.finishUtterance();
            }
          }, this.silenceDurationMs);
        }
      } else {
        // Keep a rolling pre-roll buffer while waiting for speech to begin
        preRollChunks.push(chunk);
        if (preRollChunks.length > maxPreRoll) {
          preRollChunks.shift();
        }
      }
    }
  }

  /** Cancel a pending pause hint; if one was already sent, tell the backend speech resumed. */
  private clearPauseHint(notifyResume: boolean): void {
    if (this.pauseTimer) {
      clearTimeout(this.pauseTimer);
      this.pauseTimer = null;
    }
    if (this.pauseSent) {
      this.pauseSent = false;
      if (notifyResume) {
        this.flushFrames();
        this.api.sendWsMessage({ type: 'audio_resume' });
      }
    }
  }

  /** Buffer a chunk and send a binary frame to the backend once ~100 ms of audio is queued. */
  private queueFrame(chunk: Float32Array): void {
    this.chunkCount++;
    this.pendingFrames.push(chunk);
    this.pendingSamples += chunk.length;
    if (this.pendingSamples >= this.sampleRate / 10) {
      this.flushFrames();
    }
  }

  private flushFrames(): void {
    if (this.pendingSamples === 0) return;
    const pcm = new Int16Array(this.pendingSamples);
    let offset = 0;
    for (const frame of this.pendingFrames) {
      for (let i = 0; i < frame.length; i++) {
        const s = Math.max(-1, Math.min(1, frame[i]));
        pcm[offset++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
    }
    this.pendingFrames = [];
    this.pendingSamples = 0;
    this.api.sendWsBinary(pcm.buffer);
  }

  /** Flush remaining audio and tell the backend the utterance is complete (if it had enough audio). */
  private endUtterance(): boolean {
    this.clearPauseHint(false);
    this.flushFrames();
    const hadSpeech = this.chunkCount > 5;
    this.chunkCount = 0;
    if (hadSpeech) {
      this.api.sendWsMessage({ type: 'audio_end' });
      this._utteranceEnded.update((c) => c + 1);
    }
    return hadSpeech;
  }

  private finishUtterance(): void {
    this.lastUtteranceEndTime = Date.now();
    this.consecutiveSpeechFrames = 0;
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    this.vadActive = false;
    this.endUtterance();
  }

  stopRecording(): void {
    this.lastUtteranceEndTime = 0;
    this.consecutiveSpeechFrames = 0;
    if (!this._isRecording() && this.chunkCount === 0) {
      return;
    }

    this._isRecording.set(false);
    this.vadActive = false;
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }

    if (this.workletNode) {
      this.workletNode.port.onmessage = null;
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.gainNode) {
      this.gainNode.disconnect();
      this.gainNode = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }

    this._audioLevel.set(0);

    // Send any utterance still in progress so it is not lost when the microphone is toggled off
    this.endUtterance();
  }
}
