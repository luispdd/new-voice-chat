import { ComponentFixture, TestBed } from '@angular/core/testing';
import { VoiceInputComponent } from './voice-input.component';

describe('VoiceInputComponent', () => {
  let component: VoiceInputComponent;
  let fixture: ComponentFixture<VoiceInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VoiceInputComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(VoiceInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
