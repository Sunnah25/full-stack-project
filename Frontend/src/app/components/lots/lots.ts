import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CurrencyPipe } from '@angular/common';
import { catchError, map, of, switchMap, tap } from 'rxjs';
import { WebService } from '../../services/web-service';
import { Lot } from '../../models';

@Component({
  selector: 'app-lots',
  imports: [RouterLink, CurrencyPipe],
  templateUrl: './lots.html',
  styleUrl: './lots.css'
})
export class Lots implements OnInit {
  lots = signal<Lot[]>([]);   //3
  loading = signal(true);
  error = signal('');
  page = signal(1);
  size = signal(6);
  sizeOptions = [6, 12, 24];

  constructor(private web: WebService, private route: ActivatedRoute, private router: Router) {}

  ngOnInit() {
    // The page and page size live in the URL (/lots?page=2&size=12),
    // so refresh and the browser Back button keep the user's place.
    this.route.queryParamMap.pipe(
      map(p => ({
        page: Math.max(1, Number(p.get('page')) || 1),
        size: this.sizeOptions.includes(Number(p.get('size'))) ? Number(p.get('size')) : 6
      })),
      tap(q => {
        this.page.set(q.page);
        this.size.set(q.size);
        this.loading.set(true);
        this.error.set('');
      }),
      switchMap(q => this.web.getLots(q.page, q.size).pipe(
        catchError(err => {
          this.error.set(err.status === 0
            ? 'Cannot reach the server. Please check that the API is running and try again.'
            : (err.error?.error ?? 'Something went wrong. Please try again.'));
          return of(null);
        })
      ))
    ).subscribe(result => {
      this.loading.set(false);
      if (result) this.lots.set(result);
    });
  }

  goTo(page: number) {
    this.router.navigate([], { queryParams: { page, size: this.size() } });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  changeSize(value: string) {
    this.router.navigate([], { queryParams: { page: 1, size: Number(value) } });
  }

  retry() { this.goTo(this.page()); }

  hasNext() { return this.lots().length === this.size(); }

  // Availability helpers (colour + text, so meaning never depends on colour alone)
  badgeClass(lot: Lot) {
    const ratio = lot.num_available_spaces / lot.total_spaces;
    if (lot.num_available_spaces === 0) return 'bg-danger';
    return ratio <= 0.25 ? 'bg-warning text-dark' : 'bg-success';
  }
  badgeText(lot: Lot) {
    if (lot.num_available_spaces === 0) return 'Full';
    const ratio = lot.num_available_spaces / lot.total_spaces;
    return ratio <= 0.25 ? 'Limited' : 'Available';
  }
}