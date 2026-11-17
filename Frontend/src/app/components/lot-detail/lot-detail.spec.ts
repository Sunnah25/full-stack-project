import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LotDetail } from './lot-detail';

describe('LotDetail', () => {
  let component: LotDetail;
  let fixture: ComponentFixture<LotDetail>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LotDetail],
    }).compileComponents();

    fixture = TestBed.createComponent(LotDetail);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
