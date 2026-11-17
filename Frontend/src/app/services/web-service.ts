import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Lot, SearchResult } from '../models';

@Injectable({ providedIn: 'root' })
export class WebService {
  private api = 'http://127.0.0.1:5001/api/v1.0';

  constructor(private http: HttpClient) {}

  // GET /parking_lots?pn=&ps=
  getLots(page: number, size: number): Observable<Lot[]> {
    return this.http.get<Lot[]>(`${this.api}/parking_lots?pn=${page}&ps=${size}`);
  }

  // GET /parking_lots/<id>
  getLot(id: string): Observable<Lot> {
    return this.http.get<Lot>(`${this.api}/parking_lots/${id}`);
  }

  // GET /parking_lots/search?lat=&lng=&radius=&start=&end=
  searchLots(p: { lat: number; lng: number; radius: number; start: string; end: string }):
      Observable<SearchResult[]> {
    const params = new HttpParams()
      .set('lat', p.lat)
      .set('lng', p.lng)
      .set('radius', p.radius)
      .set('start', p.start)
      .set('end', p.end);
    return this.http.get<SearchResult[]>(`${this.api}/parking_lots/search`, { params });   //4
  }
}