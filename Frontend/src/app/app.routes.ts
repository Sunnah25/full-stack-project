import { Routes } from '@angular/router';
import { Home } from './components/home/home';
import { Lots } from './components/lots/lots';
import { LotDetail } from './components/lot-detail/lot-detail';
import { NotFound } from './components/not-found/not-found';
import { Search } from './components/search/search';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'lots', component: Lots },
  { path: 'lots/:id', component: LotDetail },
  { path: 'lots/:id', component: LotDetail },
  { path: 'search', component: Search },
  // more routes are added here in the next steps
  { path: '**', component: NotFound }   // must stay last
];