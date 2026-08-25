import { Component, input, output, ElementRef, ViewChild, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message } from '../core/api.service';

@Component({
  selector: 'app-chat-history',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="chat-history-container" #scrollContainer>
      <div *ngIf="messages().length === 0" class="empty-state">
        <div class="empty-icon"><i class="pi pi-comments"></i></div>
        <h3>Voice AI Companion</h3>
        <p>Speak with the microphone or type below to start chatting.</p>
      </div>

      <div
        *ngFor="let msg of messages()"
        class="message-wrapper"
        [ngClass]="msg.role === 'user' ? 'user-wrapper' : 'assistant-wrapper'"
      >
        <div class="avatar" [ngClass]="[msg.role, msg.is_error ? 'error' : '']">
          <i class="pi" [ngClass]="msg.role === 'user' ? 'pi-user' : (msg.is_error ? 'pi-exclamation-triangle' : 'pi-sparkles')"></i>
        </div>

        <div class="bubble" [ngClass]="[msg.role, msg.is_error ? 'error' : '']">
          <div class="content">{{ msg.text }}</div>
          <div class="meta">
            <span *ngIf="msg.timestamp" class="timestamp">{{ msg.timestamp | date:'shortTime' }}</span>
            <button
              *ngIf="msg.role === 'assistant' && !msg.is_error"
              class="audio-btn"
              (click)="onPlayAudio.emit(msg.text)"
              title="Listen to response"
            >
              <i class="pi pi-volume-up"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Live Typing / Streaming / Loading Indicator -->
      <div *ngIf="isStreaming()" class="message-wrapper assistant-wrapper">
        <div class="avatar assistant">
          <i class="pi pi-sparkles"></i>
        </div>
        <div class="bubble assistant" [ngClass]="{ streaming: streamingText(), loading: !streamingText() }">
          <div *ngIf="streamingText()" class="content">{{ streamingText() }}<span class="cursor">▊</span></div>
          <div *ngIf="!streamingText()" class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .chat-history-container {
      flex: 1;
      overflow-y: auto;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .empty-state {
      margin: auto;
      text-align: center;
      color: var(--text-muted);

      .empty-icon {
        font-size: 3rem;
        color: var(--accent-blue);
        margin-bottom: 1rem;
      }

      h3 {
        font-size: 1.4rem;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
      }
    }

    .message-wrapper {
      display: flex;
      gap: 0.75rem;
      max-width: 80%;

      &.user-wrapper {
        align-self: flex-end;
        flex-direction: row-reverse;
      }

      &.assistant-wrapper {
        align-self: flex-start;
      }
    }

    .avatar {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      &.user {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #fff;
      }

      &.assistant {
        background: linear-gradient(135deg, #7c3aed, #9333ea);
        color: #fff;
      }

      &.error {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: #fff;
      }
    }

    .bubble {
      padding: 0.85rem 1.15rem;
      border-radius: 18px;
      font-size: 0.95rem;
      line-height: 1.5;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);

      &.user {
        background: var(--bubble-user);
        color: #ffffff;
        border-bottom-right-radius: 4px;
      }

      &.assistant {
        background: var(--bubble-bot);
        color: var(--text-primary);
        border: 1px solid var(--border-glass);
        border-bottom-left-radius: 4px;

        &.error {
          background: rgba(239, 68, 68, 0.15);
          border: 1px solid rgba(239, 68, 68, 0.4);
          color: #f87171;
        }

        &.loading {
          padding: 0.75rem 1rem;
        }
      }

      .content {
        white-space: pre-wrap;
        word-break: break-word;
      }

      .meta {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 0.4rem;
        font-size: 0.75rem;
        opacity: 0.8;
      }

      .audio-btn {
        background: transparent;
        border: none;
        color: var(--accent-cyan);
        cursor: pointer;
        font-size: 0.85rem;
        padding: 2px 4px;
        border-radius: 4px;
        transition: background 0.2s;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
        }
      }
    }

    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 4px 6px;

      span {
        width: 7px;
        height: 7px;
        background: var(--accent-cyan);
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out both;

        &:nth-child(1) { animation-delay: -0.32s; }
        &:nth-child(2) { animation-delay: -0.16s; }
        &:nth-child(3) { animation-delay: 0s; }
      }
    }

    @keyframes typing {
      0%, 80%, 100% {
        transform: scale(0.3);
        opacity: 0.3;
      }
      40% {
        transform: scale(1);
        opacity: 1;
      }
    }

    .cursor {
      display: inline-block;
      margin-left: 2px;
      color: var(--accent-cyan);
      animation: blink 0.8s infinite;
    }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0; }
    }
  `],
})
export class ChatHistoryComponent implements AfterViewChecked {
  messages = input<Message[]>([]);
  isStreaming = input<boolean>(false);
  streamingText = input<string>('');
  onPlayAudio = output<string>();

  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch (err) {}
  }
}
