# Smart Parking Management System API

A RESTful API for parking reservation and management with **Flask** and **MongoDB**. users will be able to search for parking lots, book spaces, check in and out and get recommendations. Lot admins can approve reservations, manage lots, check vehicles in and out, and monitor occupancy and revenue.

- **Base URL (local):** `http://127.0.0.1:5001/api/v1.0`
- **Automated tests:** 45 Postman requests, 186 assertions, 0 failures ([public documentation](https://documenter.getpostman.com/view/54103732/2sBYHUULpy))

---

## Table of contents
 
1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Project structure](#project-structure)
4. [Getting started](#getting-started)
5. [Sample dataset](#sample-dataset)
6. [Authentication and roles](#authentication-and-roles)
7. [Business rules](#business-rules)
8. [API reference](#api-reference)
9. [Data model](#data-model)
10. [Error handling](#error-handling)
11. [Testing](#testing)


---

## Features

**Public (role `guest`)**
- Browse and search parking lots by location, radius and time window, with free space and total price calculation
 
**Drivers (role `user`)**
- Register, log in (HTTP Basic auth), view their account and log out (token blacklisting)
- Browse and search parking lots by location, radius and time window, with free space and total price calculation
- Submit, view, update and cancel reservations
- Check in and check out of a reservation, with the cost calculated automatically
- View session history per reservation
- Get up to five recommended lots, scored by distance, price and availability

**Administrators (role `admin`)**
- Create, update and delete parking lots, up to 7 managed lots per admin
- View managed lots and their reservations (paginated, filterable by status)
- Approve or reject pending reservations, and correct a vehicle number
- Check vehicles in and out on behalf of drivers
- View live occupancy and revenue across managed lots

**Platform**
- JWT authentication (30-minute tokens) with a server-side logout blacklist
- Geospatial queries (MongoDB `2dsphere` index)
- Consistent JSON error responses
- Reservation data is kept in sync across the user, parking lot and admin documents

---

## Tech stack
 
- **Language:** Python 3
- **Framework:** Flask
- **Database:** MongoDB (`ParkingDB`)
- **Database Driver:** PyMongo
- **Authentication:** JWT (PyJWT, HS256)
- **Configuration:** python-dotenv
- **Testing:** Postman
 
---

## Project structure
 
```
full-stack-project/
├── app.py                  # Application factory, blueprint registration, JSON error handlers
├── extensions.py           # MongoDB client, collections and the 2dsphere index
├── auth_utils.py           # @login_required(role) decorator
├── helpers.py              # Shared logic: responses, time, pagination, availability, sessions
├── blueprints/
│   ├── auth.py             # Register, login, me, logout
│   ├── parking_lots.py     # Public lot views and search, admin lot CRUD
│   ├── reservations.py     # Driver reservations and recommendations (/me/...)
│   ├── sessions.py         # Driver check-in, check-out and history
│   └── admin.py            # Admin reservation, check-in/out, occupancy and revenue tools
└── README.md
```
 
Datasets

```
full-stack-dataset/
├── data_gen.py             # Script that generated the demo dataset (seed 42)
├── users.json              # Demo users and admins (100)
├── parking_lots.json       # Demo parking lots
└── blacklist.json          # Blacklisted tokens
```

---

## Getting started
 
### Requrements
- Python 3.9 or later
- A MongoDB server running on `mongodb://localhost:27017`

### Installation
 
```bash
git clone https://github.com/Sunnah25/full-stack-project.git
cd full-stack-project
 
 
pip install flask pymongo pyjwt python-dotenv
```
 
 
### Configuration
 
Create a `.env` file in the project root:
 
```
SECRET_KEY=a long random string
```
 
`SECRET_KEY` is required. The app raises a `KeyError` at start-up without it, and it signs and verifies all JWTs. The MongoDB connection string is set in `extensions.py`.
 
### Load the demo data
 
```bash
mongoimport --db ParkingDB --collection users        --file users.json        --jsonArray
mongoimport --db ParkingDB --collection parking_lots --file parking_lots.json --jsonArray
```
 
The `blacklist` collection is created automatically on the first logout.


### Run
 
Right click on app.py and select open in integrated terminal. And then run:

```bash
python app.py
```
 
The API is served on **http://127.0.0.1:5001** in debug mode. `GET /` returns a welcome page.
 
---

## Sample dataset
 
`data_gen.py` generates the data deterministically (`random.seed(42)`) around a simulated "now" of **2026-10-15 12:00 UTC**.
 
| Item | Count / detail |
|---|---|
| Users | 70 drivers, `<name>@example.com` |
| Admins | 30, `admin.<name>@example.com`, 1 to 5 lots each |
| Parking lots | 100 (`P0001` to `P0100`) in central London, 6 to 30 spaces, £2.50 to £9.00 per hour |
| Reservations | 186 across statuses: 60 completed, 57 cancelled, 35 pending, 34 active |
| Reservation length | 1 to 3 days, 0 to 5 per user |
 
Each seeded password is one of five values listed in `data_gen.py` and picked at random per account. Passwords are stored as SHA-256 hashes.
 
Example account: `admin.oliver@example.com` manages `P0001`.
 
---

## Authentication and roles
 
1. **Register** with `POST /auth/register`.
2. **Log in** with `POST /auth/login` using **HTTP Basic Auth** (email as username). The response contains a JWT valid for **30 minutes**.
3. Send the token on protected requests in the **`x-access-token`** header.
4. **Log out** with `GET /auth/logout`. The token is stored in the `blacklist` collection and rejected afterwards.

| Role | Can do |
|---|---|
| Public | View, search lots, register, log in |
| `user` | Everything under `/me/...` for their own reservations and sessions |
| `admin` | Lot management and `/admin/...`, restricted to lots they manage |
 
The decorator checks the token in this order, which determines the error returned:
 
| Condition | Status | Message |
|---|---|---|
| Header missing | 401 | `Token required` |
| Expired | 401 | `Token expired` |
| Invalid signature or format | 401 | `Invalid token` |
| Logged out | 401 | `Token has been logged out` |
| User no longer exists | 404 | `User not found` |
| Wrong role | 403 | `User access only` or `Admin access only` |
 
---
 
## Business rules
 
**Reservations**
- `parking_id`, `vehicle_number`, `start_time` and `end_time` are required.
- Times are ISO-8601 with a timezone (for example `2026-11-01T09:00:00Z`). The start must be in the future and the end after the start.
- A driver may have only **one pending reservation** at a time.
- A reservation is accepted only if the lot has a free space for the whole period. Overlapping reservations that are not `cancelled` or `rejected` count as taking a space.
- **Pending:** the driver may change the vehicle number and times, and the lot must still have space.
- **Approved:** the driver may change only the vehicle number.
- Only **pending** or **approved** reservations can be updated or cancelled.

**Sessions, check-in and check-out**
- Only an **approved** reservation can be checked in.
- A driver cannot be checked in twice (no other `active` reservation).
- Check-in fails with `409` if the lot is full.
- Check-out requires an `active` reservation and an open session.
- **Cost** is the total time across all movements of the session, in hours, multiplied by the lot's `price_per_hour`, rounded to 2 decimals.
- Completing a session updates the lot's availability history and adds to its `income`.

**Parking lots**
- `total_spaces` must be between **6 and 30**, `price_per_hour` greater than 0, and latitude and longitude valid.
- An admin can manage at most **7 lots**.
- Total spaces cannot be set below the number of vehicles currently parked.
- A lot with any reservation cannot be deleted.
- Public lot views hide `reservations`, `income` and `availability_history`.

**Search and recommendations**
- Search distance uses an equirectangular approximation (1 degree latitude ≈ 111 km). `radius` defaults to 5 km. Results are sorted by distance.
- Recommendations use MongoDB `$near` on the `2dsphere` index, only lots with free spaces, and return the top 5. The score is:
```
score = 0.4 × (1 − distance / farthest)
      + 0.3 × (1 − price / most_expensive)
      + 0.3 × (free_spaces / total_spaces)
```
 
**Pagination:** `pn` (page, default 1) and `ps` (page size, default 10). Both must be positive integers.
 
---
 
## API reference
 
All paths are relative to `/api/v1.0`. Request bodies are **form data** (`application/x-www-form-urlencoded` or multipart) and responses are JSON. The numbers in the first column match the comments in the source code.
 
### Authentication
 
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 4 | POST | `/auth/register` | none | Create a driver account. Fields: `name`, `email`, `password` (min. 6 chars). Returns `201`, or `409` if the email exists. |
| 5 | POST | `/auth/login` | Basic | Returns `token`, `user_id` and `role`. `401` for wrong credentials. |
| 6 | GET | `/auth/me` | any | Own account (admins also get `managed_parking_lots`). |
| 27 | GET | `/auth/logout` | any | Blacklists the current token. |
 
### Public parking lots
 
| # | Method | Path | Description |
|---|---|---|---|
| 1 | GET | `/parking_lots?pn=&ps=` | Paginated lot summaries sorted by `parking_id`. |
| 2 | GET | `/parking_lots/<parking_id>` | One lot with private fields hidden. `404` if unknown. |
| 3 | GET | `/parking_lots/search` | Query: `lat`, `lng`, `start`, `end` (required), `radius` (km, default 5). Returns lots with free spaces, `distance_km`, `free_spaces`, `price_per_hour` and `total_price`. |
 
### Driver reservations (`user` role)
 
| # | Method | Path | Description |
|---|---|---|---|
| 7 | POST | `/me/reservations` | Create a reservation. Fields: `parking_id`, `vehicle_number`, `start_time`, `end_time`. Returns `201` with `reservation_id`, `status` and `url`. |
| 8 | GET | `/me/reservations?status=` | List own reservations. Valid statuses: `pending`, `approved`, `rejected`, `active`, `completed`, `cancelled`. |
| 9 | GET | `/me/reservations/<reservation_id>` | One own reservation. |
| 10 | PUT | `/me/reservations/<reservation_id>` | Update `vehicle_number`, `start_time` and/or `end_time`, subject to status rules. |
| 11 | PUT | `/me/reservations/<reservation_id>/cancel` | Cancel a pending or approved reservation. |
| 15 | GET | `/me/recommendations?lat=&lng=&radius=` | Top 5 lots by score. Any logged-in role. |
 
### Driver sessions (`user` role)
 
| # | Method | Path | Description |
|---|---|---|---|
| 12 | POST | `/me/reservations/<reservation_id>/sessions/check-in` | Start a session. Returns `201` with the new session. |
| 13 | POST | `/me/reservations/<reservation_id>/sessions/<session_id>/check-out` | End the session, calculate the cost, and complete the reservation. |
| 14 | GET | `/me/reservations/<reservation_id>/sessions/history` | All sessions with costs and movements. |
 
### Admin: parking lots (`admin` role)
 
| # | Method | Path | Description |
|---|---|---|---|
| 16 | POST | `/parking_lots` | Create a lot. Fields: `street`, `city`, `postcode`, `latitude`, `longitude`, `total_spaces`, `price_per_hour`. The ID is auto-generated (`P0101`, ...). |
| 17 | PUT | `/parking_lots/<parking_id>` | Update any subset of those fields on a managed lot. |
| 18 | DELETE | `/parking_lots/<parking_id>` | Delete a managed lot with no reservations. |
| 25 | GET | `/admin/parking_lots` | Summaries of all managed lots. |
| 26 | GET | `/admin/parking_lots/<parking_id>` | One managed lot (`403` if not managed). |
 
### Admin: reservations and operations (`admin` role)
 
| # | Method | Path | Description |
|---|---|---|---|
| 19 | GET | `/admin/parking_lots/<parking_id>/reservations?status=&pn=&ps=` | Reservations for a managed lot. |
| 20 | PUT | `/admin/parking_lots/<parking_id>/reservations/<reservation_id>` | `status` = `approved` or `rejected` (pending only) and/or `vehicle_number`. |
| 21 | POST | `/admin/parking_lots/<parking_id>/reservations/<reservation_id>/check-in` | Check a vehicle in for the driver. |
| 22 | POST | `/admin/parking_lots/<parking_id>/reservations/<reservation_id>/sessions/<session_id>/check-out` | Check a vehicle out. |
| 23 | GET | `/admin/occupancy` | Per lot: `total_spaces`, `occupied_spaces`, `num_available_spaces`, `occupancy_rate` (%), `vehicles_inside`. |
| 24 | GET | `/admin/revenue` | `total_revenue`, `completed_reservations` and a `by_parking_lot` breakdown. |
 

---
 
## Data model
 
MongoDB database `ParkingDB`, three collections.
 
**`users`** holds both drivers and admins.
 
```jsonc
{
  "role": "user",                       // "user" | "admin"
  "user_id": "lisa@example.com",      // the email is the ID
  "name": "Joshua",
  "password_hash": "<sha256>",
  // drivers:
  "reservation_details": [ { /* reservation */ } ],
  // admins:
  "managed_parking_lots": [
    { "parking_id": "P0001", "reservation_refs": [ { /* reservation + user_id */ } ] }
  ]
}
```
 
**`parking_lots`**
 
```jsonc
{
  "parking_id": "P0001",
  "address": { "street": "1 High Street", "city": "London", "postcode": "SW1 1AA" },
  "location": { "type": "Point", "coordinates": [-0.1278, 51.5074] },   // [lng, lat]
  "total_spaces": 26,
  "num_available_spaces": 26,
  "updated_at": "2026-10-15T12:00:00Z",
  "price_per_hour": 3.22,
  "administrators": [ { "user_id": "admin.oliver@example.com", "name": "Oliver" } ],
  "reservations": [ { /* reservation + user_id */ } ],
  "income": { "total_income": 0.0, "completed_reservations": 0, "updated_at": "..." },
  "availability_history": [
    { "updated_at": "...", "num_available_spaces": 26,
      "vehicles_inside": [ { "reservation_id": "R000001", "vehicle_number": "AB12 CDE" } ] }
  ]
}
```
 
**Reservation** (embedded)
 
```jsonc
{
  "reservation_id": "R000001",
  "parking_id": "P0091",
  "vehicle_number": "AB12 CDE",
  "start_time": "2026-10-20T09:00:00Z",
  "end_time": "2026-10-22T18:00:00Z",
  "status": "pending",
  "created_at": "2026-10-16T01:00:00Z",
  "sessions": [
    { "session_id": "S000001", "total_cost": 14.5,
      "movements": [ { "check_in_time": "...", "check_out_time": "..." } ] }
  ]
}
```
 
**`blacklist`**: `{ "token": "<jwt>" }`, one document per logged-out token.
 
**Design note:** each reservation is stored in **three places**, the driver's document, the lot's document, and the `reservation_refs` of every admin managing that lot. The helper `update_everywhere()` applies each change to all three copies. This keeps reads fast, but writes must always go through that helper.
 
**ID generation:** `R` + 6 digits for reservations, `S` + 6 for sessions, `P` + 4 for lots. Each is the highest existing number plus one.
 
---
 
## Error handling
 
Errors are always JSON: `{ "error": "<message>" }`.
 
| Status | Meaning |
|---|---|
| 400 | Missing or invalid input, bad pagination, bad time format or range |
| 401 | Missing, expired, invalid or logged-out token, or wrong login credentials |
| 403 | Wrong role, or an admin acting on a lot they do not manage |
| 404 | Unknown lot, reservation, session or user, or unknown route |
| 405 | Method not allowed |
| 409 | State conflict: duplicate email, no free space, pending limit, invalid status transition, lot full, and similar |
| 500 | Internal server error |
 
An invalid `status` filter returns `400` with the list of `allowed_statuses`.
 
---
 
## Testing
 
The API is tested with the Postman collection **Parking API Tests**:
[documenter.getpostman.com/view/54103732/2sBYHUULpy](https://documenter.getpostman.com/view/54103732/2sBYHUULpy)
 
**Latest recorded run** (27 Oct 2026): 45 requests, **186 passed, 0 failed**, finished in about 0.4 s against `http://127.0.0.1:5001`.
 
### What is covered
 
| Area | Requests | Checks |
|---|---|---|
| Public lots (1-3) | View all, view one, invalid ID (404), search, search with a bad `lat` (400) | Status, JSON, array shape, public fields only, private fields hidden, results ordered by distance, response time under 2 s |
| Auth (4-6, 27) | Register, duplicate (409), login, wrong password and wrong email (401), `/me`, `/me` without token (401), logout, reuse of the logged-out token (401) | Token returned, role, password hash never exposed, no token on failure |
| Driver reservations (7-11) | Submit (201), missing field (400), list, view one, invalid ID (404), update, cancel, and 2nd and 3rd submissions | Pending status, URL returned, required fields, status becomes `cancelled` |
| Driver sessions (12-14) | Check-in, check-out, history | Session ID, open movement, calculated cost, check-out time recorded |
| Recommendations (15) | Nearby recommendations | At most 5 results, required fields, only lots with free spaces, sorted by descending score |
| Admin lots (16-18, 25, 26) | Create (201), update, delete, delete with reservations (409), list managed lots, view one | New ID and URL, private data excluded, ID matches |
| Admin reservations (19-22) | List, filter by status, invalid pagination (400), approve, admin check-in, admin check-out | All reservations belong to the lot, all match the status filter, status becomes `approved`, session cost calculated |
| Admin analytics (23-24) | Occupancy, revenue | Consistent occupied/available values, no duplicate lot IDs, totals equal the per-lot breakdown |
 
The requests run in order and share variables (tokens, reservation and session IDs), so the collection should be run as a whole.
 
### Running the tests
1. Reload the data and start the server on port 5001.
2. Import the collection into Postman, or open the published documentation and use **Run in Postman**.
3. The environment should point at `http://127.0.0.1:5001` and that the admin login in the collection matches an admin from the dataset (the run used the admin of `P0001`).
4. Change the user mail and use a unique email for registration otherwise most of the tests will fail.
5. Use the **Collection Runner** to run the full collection.
Because the tests create, approve and delete data, reload the dataset before each full run and change the usermail for registration.
 

---


Front-end coming later...