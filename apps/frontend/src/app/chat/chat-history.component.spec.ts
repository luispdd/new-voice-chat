import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ChatHistoryComponent } from './chat-history.component';

describe('ChatHistoryComponent', () => {
  let component: ChatHistoryComponent;
  let fixture: ComponentFixture<ChatHistoryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatHistoryComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ChatHistoryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should scroll to bottom when shouldAutoScroll is true', () => {
    const el = component.scrollContainer()!.nativeElement;
    Object.defineProperty(el, 'scrollHeight', { value: 500, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 200, configurable: true });

    component.shouldAutoScroll = true;
    component.scrollToBottom();

    expect(el.scrollTop).toBe(500);
  });

  it('should detect when user has scrolled up and not auto-scroll', () => {
    const el = component.scrollContainer()!.nativeElement;
    Object.defineProperty(el, 'scrollHeight', { value: 1000, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 300, configurable: true });
    el.scrollTop = 100; // Scrolled far from bottom (1000 - 100 - 300 = 600 > 60)

    component.onScroll();
    expect(component.shouldAutoScroll).toBe(false);

    el.scrollTop = 100;
    component.scrollToBottom();
    // scrollTop should remain unchanged since shouldAutoScroll is false
    expect(el.scrollTop).toBe(100);
  });

  it('should re-enable auto-scroll when user scrolls near the bottom', () => {
    const el = component.scrollContainer()!.nativeElement;
    Object.defineProperty(el, 'scrollHeight', { value: 1000, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 300, configurable: true });

    component.shouldAutoScroll = false;
    el.scrollTop = 680; // Distance to bottom: 1000 - 680 - 300 = 20 <= 60

    component.onScroll();
    expect(component.shouldAutoScroll).toBe(true);
  });

  it('should force scroll to bottom when force is true', () => {
    const el = component.scrollContainer()!.nativeElement;
    Object.defineProperty(el, 'scrollHeight', { value: 1000, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 300, configurable: true });
    el.scrollTop = 100;
    component.shouldAutoScroll = false;

    component.scrollToBottom(true);
    expect(component.shouldAutoScroll).toBe(true);
    expect(el.scrollTop).toBe(1000);
  });
});
