import { Injectable } from '@angular/core';
import { Subject, BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AudioRecordService {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private analyser: AnalyserNode | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private gainNode: GainNode | null = null;

  private isRecording$ = new BehaviorSubject<boolean>(false);
  private audioChunks: Float32Array[] = [];
  private audioLevel$ = new Subject<number>();
  private audioChunkReady$ = new Subject<Blob>();
  private sampleRate = 16000;

  // VAD parameters
  private vadActive = false;
  private silenceTimer: any = null;
  private readonly silenceThreshold = 0.018;
  private readonly silenceDurationMs = 1500;

  get isRecording(): Observable<boolean> {
    return this.isRecording$.asObservable();
  }

  get isRecordingActive(): boolean {
    return this.isRecording$.value;
  }

  get audioLevel(): Observable<number> {
    return this.audioLevel$.asObservable();
  }

  get onAudioChunkReady(): Observable<Blob> {
    return this.audioChunkReady$.asObservable();
  }

  async startRecording(): Promise<void> {
    if (this.isRecording$.value) return;

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

      this.scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);
      this.gainNode = this.audioContext.createGain();
      this.gainNode.gain.value = 0; // Mute gain node to prevent mic input echoing to speakers

      this.audioChunks = [];
      this.vadActive = false;
      this.isRecording$.next(true);

      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      this.scriptProcessor.onaudioprocess = (e) => {
        if (!this.isRecording$.value) return;
        const inputData = e.inputBuffer.getChannelData(0);
        this.audioChunks.push(new Float32Array(inputData));

        // Calculate RMS audio level
        this.analyser?.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        this.audioLevel$.next(Math.min(rms * 5, 1)); // Normalized 0-1

        // Voice Activity Detection logic
        if (rms > this.silenceThreshold) {
          this.vadActive = true;
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
          }
        } else if (this.vadActive) {
          if (!this.silenceTimer) {
            this.silenceTimer = setTimeout(() => {
              if (this.vadActive && this.audioChunks.length > 5) {
                this.stopRecording();
              }
            }, this.silenceDurationMs);
          }
        }
      };

      source.connect(this.analyser);
      this.analyser.connect(this.scriptProcessor);
      this.scriptProcessor.connect(this.gainNode);
      this.gainNode.connect(this.audioContext.destination);

    } catch (err) {
      console.error('Error starting audio recording:', err);
      this.stopRecording();
      throw err;
    }
  }

  stopRecording(): Blob | null {
    if (!this.isRecording$.value && this.audioChunks.length === 0) {
      return null;
    }

    this.isRecording$.next(false);
    this.vadActive = false;
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }

    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor = null;
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

    this.audioLevel$.next(0);

    if (this.audioChunks.length > 5) {
      const wavBlob = this.exportWAV(this.audioChunks, this.sampleRate);
      this.audioChunks = [];
      this.audioChunkReady$.next(wavBlob);
      return wavBlob;
    }
    this.audioChunks = [];
    return null;
  }

  private exportWAV(chunks: Float32Array[], sampleRate: number): Blob {
    let totalLength = 0;
    for (const chunk of chunks) {
      totalLength += chunk.length;
    }

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Convert to 16-bit PCM WAV
    const buffer = new ArrayBuffer(44 + merged.length * 2);
    const view = new DataView(buffer);

    // RIFF chunk descriptor
    this.writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + merged.length * 2, true);
    this.writeString(view, 8, 'WAVE');

    // fmt sub-chunk
    this.writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // byte rate
    view.setUint16(32, 2, true); // block align
    view.setUint16(34, 16, true); // bits per sample

    // data sub-chunk
    this.writeString(view, 36, 'data');
    view.setUint32(40, merged.length * 2, true);

    // Write samples
    let index = 44;
    for (let i = 0; i < merged.length; i++) {
      const s = Math.max(-1, Math.min(1, merged[i]));
      view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      index += 2;
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }

  private writeString(view: DataView, offset: number, string: string): void {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }
}
