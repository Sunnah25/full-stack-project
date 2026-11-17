import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { catchError, map, of, switchMap, tap } from 'rxjs';
import { WebService } from '../../services/web-service';
import { Lot } from '../../models';

@Component({
  selector: 'app-lot-detail',
  imports: [RouterLink, CurrencyPipe, DatePipe],
  templateUrl: './lot-detail.html',
  styleUrl: './lot-detail.css'
})
export class LotDetail implements OnInit {
  lot = signal<Lot | null>(null);
  loading = signal(true);
  error = signal('');
  notFound = signal(false);

  constructor(private web: WebService, private route: ActivatedRoute) {}

  ngOnInit() {
    this.route.paramMap.pipe(
      map(p => p.get('id') ?? ''),
      tap(() => { this.loading.set(true); this.error.set(''); this.notFound.set(false); }),
      switchMap(id => this.web.getLot(id).pipe(
        catchError(err => {
          if (err.status === 404) this.notFound.set(true);
          else this.error.set(err.status === 0
            ? 'Cannot reach the server. Please check that the API is running and try again.'
            : (err.error?.error ?? 'Something went wrong.'));
          return of(null);
        })
      ))
    ).subscribe(result => {
      this.loading.set(false);
      this.lot.set(result);
    });
  }

  // coordinates are stored as [lng, lat]
  mapsUrl(lot: Lot) {
    const [lng, lat] = lot.location.coordinates;
    return `https://www.google.com/maps?q=${lat},${lng}`;
  }

  occupancy(lot: Lot) {
    return Math.round(((lot.total_spaces - lot.num_available_spaces) / lot.total_spaces) * 100);
  }
}