// 2. why?

export interface Address {
  street: string;
  city: string;
  postcode: string;
}

export interface Lot {
  parking_id: string;
  address: Address;
  location: { type: string; coordinates: [number, number] };  // [lng, lat]
  total_spaces: number;
  num_available_spaces: number;
  updated_at: string;
  price_per_hour: number;
}

export interface SearchResult {
  parking_id: string;
  address: Address;
  distance_km: number;
  free_spaces: number;
  price_per_hour: number;
  total_price: number;
}