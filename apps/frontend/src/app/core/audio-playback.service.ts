import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AudioPlaybackService {
  private audioContext: AudioContext | null = null;
  private isPlaying$ = new BehaviorSubject<boolean>(false);
  private queue: AudioBuffer[] = [];
  private isProcessingQueue = false;
  private currentSource: AudioBufferSourceNode | null = null;

  get isPlaying(): Observable<boolean> {
    return this.isPlaying$.asObservable();
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
    const arrayBuffer = await blob.arrayBuffer();
    await this.enqueueArrayBuffer(arrayBuffer);
  }

  async enqueueBase64Wav(b64Data: string): Promise<void> {
    const binary = atob(b64Data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    await this.enqueueArrayBuffer(bytes.buffer);
  }

  private async enqueueArrayBuffer(arrayBuffer: ArrayBuffer): Promise<void> {
    const ctx = this.initAudioContext();
    try {
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
      this.queue.push(audioBuffer);
      if (!this.isProcessingQueue) {
        this.processQueue();
      }
    } catch (err) {
      console.error('Error decoding audio data for playback:', err);
    }
  }

  private processQueue(): void {
    if (this.queue.length === 0) {
      this.isProcessingQueue = false;
      this.isPlaying$.next(false);
      return;
    }

    this.isProcessingQueue = true;
    this.isPlaying$.next(true);

    const buffer = this.queue.shift()!;
    const ctx = this.initAudioContext();

    this.currentSource = ctx.createBufferSource();
    this.currentSource.buffer = buffer;
    this.currentSource.connect(ctx.destination);

    this.currentSource.onended = () => {
      this.currentSource = null;
      this.processQueue();
    };

    this.currentSource.start(0);
  }

  stopPlayback(): void {
    this.queue = [];
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch (e) {}
      this.currentSource = null;
    }
    this.isProcessingQueue = false;
    this.isPlaying$.next(false);
  }
}
