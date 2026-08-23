import { Component, Input, Output, EventEmitter, ElementRef, ViewChild, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message } from '../core/api.service';

@Component({
  selector: 'app-chat-history',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="chat-history-container" #scrollContainer>
      <div *ngIf="messages.length === 0" class="empty-state">
        <div class="empty-icon"><i class="pi pi-comments"></i></div>
        <h3>Voice AI Companion</h3>
        <p>Speak with the microphone or type below to start chatting.</p>
      </div>

      <div
        *ngFor="let msg of messages"
        class="message-wrapper"
        [ngClass]="msg.role === 'user' ? 'user-wrapper' : 'assistant-wrapper'"
      >
        <div class="avatar" [ngClass]="msg.role">
          <i class="pi" [ngClass]="msg.role === 'user' ? 'pi-user' : 'pi-sparkles'"></i>
        </div>

        <div class="bubble" [ngClass]="msg.role">
          <div class="content">{{ msg.text }}</div>
          <div class="meta">
            <span *ngIf="msg.timestamp" class="timestamp">{{ msg.timestamp | date:'shortTime' }}</span>
            <button
              *ngIf="msg.role === 'assistant'"
              class="audio-btn"
              (click)="onPlayAudio.emit(msg.text)"
              title="Listen to response"
            >
              <i class="pi pi-volume-up"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Live Typing / Streaming Indicator -->
      <div *ngIf="isStreaming && streamingText" class="message-wrapper assistant-wrapper">
        <div class="avatar assistant">
          <i class="pi pi-sparkles"></i>
        </div>
        <div class="bubble assistant streaming">
          <div class="content">{{ streamingText }}<span class="cursor">▊</span></div>
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
  @Input() messages: Message[] = [];
  @Input() isStreaming = false;
  @Input() streamingText = '';
  @Output() onPlayAudio = new EventEmitter<string>();

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
