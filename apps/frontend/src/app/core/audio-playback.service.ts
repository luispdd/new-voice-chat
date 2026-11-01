import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class AudioPlaybackService {
  private audioContext: AudioContext | null = null;
  private queue: AudioBuffer[] = [];
  private isProcessingQueue = false;
  private currentSource: AudioBufferSourceNode | null = null;
  private playbackEpoch = 0;
  private decodeChain: Promise<void> = Promise.resolve();

  private _isPlaying = signal<boolean>(false);
  readonly isPlaying = this._isPlaying.asReadonly();

  private _isMuted = signal<boolean>(false);
  readonly isMuted = this._isMuted.asReadonly();

  setMuted(muted: boolean): void {
    this._isMuted.set(muted);
    if (muted) {
      this.stopPlayback();
    }
  }

  toggleMute(): boolean {
    const nextState = !this._isMuted();
    this.setMuted(nextState);
    return nextState;
  }

  private initAudioContext(): AudioContext {
    if (!this.audioContext || this.audioContext.state === 'closed') {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
    return this.audioContext;
  }

  async enqueueWavBlob(blob: Blob): Promise<void> {
    if (this._isMuted()) {
      return;
    }
    const arrayBuffer = await blob.arrayBuffer();
    await this.enqueueArrayBuffer(arrayBuffer);
  }

  async enqueueBase64Wav(b64Data: string): Promise<void> {
    if (this._isMuted()) {
      return;
    }
    const binary = atob(b64Data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    await this.enqueueArrayBuffer(bytes.buffer);
  }

  private enqueueArrayBuffer(arrayBuffer: ArrayBuffer): Promise<void> {
    if (this._isMuted()) {
      return Promise.resolve();
    }
    const epoch = this.playbackEpoch;
    // Chain decoding to guarantee audio chunks are decoded and queued in exact FIFO order
    this.decodeChain = this.decodeChain
      .catch(() => {})
      .then(async () => {
        if (this._isMuted() || this.playbackEpoch !== epoch) {
          return;
        }
        const ctx = this.initAudioContext();
        try {
          const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
          if (this._isMuted() || this.playbackEpoch !== epoch) {
            return;
          }
          this.queue.push(audioBuffer);
          if (!this.isProcessingQueue) {
            this.processQueue();
          }
        } catch (err) {
          console.error('Error decoding audio data for playback:', err);
        }
      });
    return this.decodeChain;
  }

  private processQueue(): void {
    if (this._isMuted() || this.queue.length === 0) {
      this.isProcessingQueue = false;
      this._isPlaying.set(false);
      return;
    }

    this.isProcessingQueue = true;
    this._isPlaying.set(true);

    const buffer = this.queue.shift()!;
    const ctx = this.initAudioContext();

    const source = ctx.createBufferSource();
    this.currentSource = source;
    source.buffer = buffer;
    source.connect(ctx.destination);

    const epoch = this.playbackEpoch;
    source.onended = () => {
      if (this.currentSource === source) {
        this.currentSource = null;
      }
      if (this.playbackEpoch === epoch) {
        this.processQueue();
      }
    };

    try {
      source.start(0);
    } catch (err) {
      console.error('Error starting audio buffer source:', err);
      if (this.playbackEpoch === epoch) {
        this.processQueue();
      }
    }
  }

  stopPlayback(): void {
    this.playbackEpoch++;
    this.decodeChain = Promise.resolve();
    this.queue = [];
    if (this.currentSource) {
      const source = this.currentSource;
      this.currentSource = null;
      source.onended = null;
      try {
        source.stop();
        source.disconnect();
      } catch (e) {}
    }
    this.isProcessingQueue = false;
    this._isPlaying.set(false);
  }
}
