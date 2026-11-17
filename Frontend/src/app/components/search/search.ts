import { Component, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CurrencyPipe } from '@angular/common';
import { WebService } from '../../services/web-service';
import { SearchResult } from '../../models';

// datetime-local inputs need "YYYY-MM-DDTHH:mm" in LOCAL time
function toLocalInput(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
// The API wants ISO-8601 with timezone, e.g. 2026-11-18T09:00:00Z
function toApiTime(local: string): string {
  return new Date(local).toISOString().split('.')[0] + 'Z';
}

@Component({
  selector: 'app-search',
  imports: [ReactiveFormsModule, RouterLink, CurrencyPipe],
  templateUrl: './search.html',
  styleUrl: './search.css'
})
export class Search implements OnInit {
  presets = [
    { name: 'Central London', lat: 51.5074, lng: -0.1278 },
    { name: 'Westminster',    lat: 51.4975, lng: -0.1357 },
    { name: 'City of London', lat: 51.5155, lng: -0.0922 },
    { name: 'Camden',         lat: 51.5390, lng: -0.1426 },
    { name: 'Canary Wharf',   lat: 51.5054, lng: -0.0235 },
    { name: 'Greenwich',      lat: 51.4826, lng: 0.0077 }
  ];
  radiusOptions = [1, 2, 5, 10, 20];

  form;
  minDate = toLocalInput(new Date());

  submitted = signal(false);
  formError = signal('');
  loading = signal(false);
  error = signal('');
  results = signal<SearchResult[] | null>(null);   // null = not searched yet
  locating = signal(false);
  locationNote = signal('');
  hours = signal(0);

  constructor(private fb: FormBuilder, private web: WebService,
              private route: ActivatedRoute, private router: Router) {
    // Default: starting in the next full hour, for 2 hours
    const start = new Date();
    start.setHours(start.getHours() + 1, 0, 0, 0);
    const end = new Date(start.getTime() + 2 * 60 * 60 * 1000);

    this.form = this.fb.nonNullable.group({
      lat: [this.presets[0].lat, [Validators.required, Validators.min(-90), Validators.max(180)]],
      lng: [this.presets[0].lng, [Validators.required, Validators.min(-180), Validators.max(180)]],
      radius: [5, [Validators.required, Validators.min(0.1)]],
      start: [toLocalInput(start), Validators.required],
      end: [toLocalInput(end), Validators.required]
    });
  }

  ngOnInit() {
    // If the URL already holds a search (refresh / Back button), restore and run it
    const q = this.route.snapshot.queryParamMap;
    if (q.has('lat') && q.has('lng') && q.has('start') && q.has('end')) {
      this.form.patchValue({
        lat: Number(q.get('lat')),
        lng: Number(q.get('lng')),
        radius: Number(q.get('radius')) || 5,
        start: toLocalInput(new Date(q.get('start')!)),
        end: toLocalInput(new Date(q.get('end')!))
      });
      this.run();
    }
  }

  choosePreset(name: string) {
    const p = this.presets.find(x => x.name === name);
    if (p) {
      this.form.patchValue({ lat: p.lat, lng: p.lng });
      this.locationNote.set('');
    }
  }

  useMyLocation() {
    if (!navigator.geolocation) {
      this.locationNote.set('Your browser does not support location. Please choose an area instead.');
      return;
    }
    this.locating.set(true);
    this.locationNote.set('');
    navigator.geolocation.getCurrentPosition(
      pos => {
        this.form.patchValue({
          lat: Number(pos.coords.latitude.toFixed(5)),
          lng: Number(pos.coords.longitude.toFixed(5))
        });
        this.locating.set(false);
        this.locationNote.set('Using your current location.');
      },
      () => {
        this.locating.set(false);
        this.locationNote.set('We could not get your location. Please choose an area instead.');
      }
    );
  }

  submit() {
    this.submitted.set(true);
    this.formError.set('');
    const v = this.form.getRawValue();

    if (this.form.invalid) {
      this.formError.set('Please fill in every field with valid values.');
      return;
    }
    if (new Date(v.end) <= new Date(v.start)) {
      this.formError.set('The end time must be after the start time.');
      return;
    }

    // Keep the search in the URL (no extra history entry)
    this.router.navigate([], {
      replaceUrl: true,
      queryParams: { lat: v.lat, lng: v.lng, radius: v.radius,
                     start: toApiTime(v.start), end: toApiTime(v.end) }
    });
    this.run();
  }

  private run() {
    const v = this.form.getRawValue();
    this.hours.set((new Date(v.end).getTime() - new Date(v.start).getTime()) / 3600000);
    this.loading.set(true);
    this.error.set('');

    this.web.searchLots({
      lat: v.lat, lng: v.lng, radius: v.radius,
      start: toApiTime(v.start), end: toApiTime(v.end)
    }).subscribe({
      next: res => { this.results.set(res); this.loading.set(false); },
      error: err => {
        this.loading.set(false);
        this.error.set(err.status === 0
          ? 'Cannot reach the server. Please check that the API is running and try again.'
          : (err.error?.error ?? 'Something went wrong. Please try again.'));
      }
    });
  }

  durationText(): string {
    const h = this.hours();
    if (h < 24) return `${Math.round(h * 10) / 10} hour${h === 1 ? '' : 's'}`;
    const days = Math.floor(h / 24), rest = Math.round(h % 24);
    return `${days} day${days === 1 ? '' : 's'}${rest ? ' ' + rest + ' h' : ''}`;
  }
}