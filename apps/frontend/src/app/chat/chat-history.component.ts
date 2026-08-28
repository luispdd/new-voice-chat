import { Component, input, output, ElementRef, viewChild, AfterViewChecked, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message } from '../core/api.service';

@Component({
  selector: 'app-chat-history',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './chat-history.component.html',
  styleUrl: './chat-history.component.scss',
})
export class ChatHistoryComponent implements AfterViewChecked {
  messages = input<Message[]>([]);
  isStreaming = input<boolean>(false);
  streamingText = input<string>('');
  onPlayAudio = output<string>();

  scrollContainer = viewChild<ElementRef<HTMLDivElement>>('scrollContainer');

  shouldAutoScroll = true;

  constructor() {
    effect(() => {
      const msgs = this.messages();
      if (msgs.length > 0) {
        const lastMsg = msgs[msgs.length - 1];
        if (lastMsg.role === 'user') {
          this.shouldAutoScroll = true;
        }
      } else {
        this.shouldAutoScroll = true;
      }
    });
  }

  ngAfterViewChecked() {
    if (this.shouldAutoScroll) {
      this.scrollToBottom();
    }
  }

  onScroll(): void {
    const container = this.scrollContainer()?.nativeElement;
    if (!container) return;
    const threshold = 60;
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    this.shouldAutoScroll = distanceToBottom <= threshold;
  }

  scrollToBottom(force = false): void {
    const container = this.scrollContainer()?.nativeElement;
    if (!container) return;
    if (force) {
      this.shouldAutoScroll = true;
    }
    if (this.shouldAutoScroll) {
      try {
        container.scrollTop = container.scrollHeight;
      } catch (err) {}
    }
  }
}
