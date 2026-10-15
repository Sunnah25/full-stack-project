import random
import json
import hashlib
from datetime import datetime, timedelta

users = [ "Oliver", "Amelia", "George", "Isla", "Harry",
    "Ava", "Jack", "Mia", "Charlie", "Sophia",
    "Noah", "Grace", "Leo", "Lily", "Oscar",
    "Freya", "Arthur", "Ella", "Henry", "Evie",
    "Theodore", "Poppy", "Thomas", "Florence", "James",
    "Emily", "William", "Rosie", "Alexander", "Ivy",
    "Joshua", "Elsie", "Edward", "Daisy", "Lucas",
    "Sienna", "Benjamin", "Alice", "Ethan", "Ruby",
    "Jacob", "Matilda", "Samuel", "Chloe", "Daniel",
    "Isabella", "Joseph", "Phoebe", "Adam", "Hannah",
    "Max", "Eleanor", "Logan", "Maisie", "Frederick",
    "Imogen", "Finley", "Jessica", "Sebastian", "Molly",
    "Harrison", "Abigail", "Dylan", "Esme", "Alfie",
    "Georgia", "Reuben", "Zara", "David", "Millie",
    "Matthew", "Erin", "Ryan", "Layla", "Nathan",
    "Amber", "Caleb", "Lucy", "Isaac", "Holly",
    "Luke", "Martha", "Aaron", "Annabelle", "Michael",
    "Emma", "Rory", "Lola", "Louis", "Violet",
    "Felix", "Arabella", "Gabriel", "Niamh", "Jude",
    "Beatrice", "Elliot", "Maya", "Patrick", "Eliza"]

roles = ["user", "admin"]

admins_ids = [
    "admin.oliver@example.com",
    "admin.amelia@example.com",
    "admin.george@example.com",
    "admin.isla@example.com",
    "admin.harry@example.com",
    "admin.ava@example.com",
    "admin.jack@example.com",
    "admin.mia@example.com",
    "admin.charlie@example.com",
    "admin.sophia@example.com",
    "admin.noah@example.com",
    "admin.grace@example.com",
    "admin.leo@example.com",
    "admin.lily@example.com",
    "admin.oscar@example.com",
    "admin.freya@example.com",
    "admin.arthur@example.com",
    "admin.ella@example.com",
    "admin.henry@example.com",
    "admin.evie@example.com"
]

normal_users_ids = [
    "theodore@example.com",
    "poppy@example.com",
    "thomas@example.com",
    "florence@example.com",
    "james@example.com",
    "emily@example.com",
    "william@example.com",
    "rosie@example.com",
    "alexander@example.com",
    "ivy@example.com",
    "joshua@example.com",
    "elsie@example.com",
    "edward@example.com",
    "daisy@example.com",
    "lucas@example.com",
    "sienna@example.com",
    "benjamin@example.com",
    "alice@example.com",
    "ethan@example.com",
    "ruby@example.com",
    "jacob@example.com",
    "matilda@example.com",
    "samuel@example.com",
    "chloe@example.com",
    "daniel@example.com",
    "isabella@example.com",
    "joseph@example.com",
    "phoebe@example.com",
    "adam@example.com",
    "hannah@example.com",
    "max@example.com",
    "eleanor@example.com",
    "logan@example.com",
    "maisie@example.com",
    "frederick@example.com",
    "imogen@example.com",
    "finley@example.com",
    "jessica@example.com",
    "sebastian@example.com",
    "molly@example.com",
    "harrison@example.com",
    "abigail@example.com",
    "dylan@example.com",
    "esme@example.com",
    "alfie@example.com",
    "georgia@example.com",
    "reuben@example.com",
    "zara@example.com",
    "david@example.com",
    "millie@example.com",
    "matthew@example.com",
    "erin@example.com",
    "ryan@example.com",
    "layla@example.com",
    "nathan@example.com",
    "amber@example.com",
    "caleb@example.com",
    "lucy@example.com",
    "isaac@example.com",
    "holly@example.com",
    "luke@example.com",
    "martha@example.com",
    "aaron@example.com",
    "annabelle@example.com",
    "michael@example.com",
    "emma@example.com",
    "rory@example.com",
    "lola@example.com",
    "louis@example.com",
    "violet@example.com",
    "felix@example.com",
    "arabella@example.com",
    "gabriel@example.com",
    "niamh@example.com",
    "jude@example.com",
    "beatrice@example.com",
    "elliot@example.com",
    "maya@example.com",
    "patrick@example.com",
    "eliza@example.com"
]

parking_lot_ids = [
    "PARK001", "PARK002", "PARK003", "PARK004", "PARK005",
    "PARK006", "PARK007", "PARK008", "PARK009", "PARK010",
    "PARK011", "PARK012", "PARK013", "PARK014", "PARK015",
    "PARK016", "PARK017", "PARK018", "PARK019", "PARK020",
    "PARK021", "PARK022", "PARK023", "PARK024", "PARK025",
    "PARK026", "PARK027", "PARK028", "PARK029", "PARK030",
    "PARK031", "PARK032", "PARK033", "PARK034", "PARK035",
    "PARK036", "PARK037", "PARK038", "PARK039", "PARK040",
    "PARK041", "PARK042", "PARK043", "PARK044", "PARK045",
    "PARK046", "PARK047", "PARK048", "PARK049", "PARK050",
    "PARK051", "PARK052", "PARK053", "PARK054", "PARK055",
    "PARK056", "PARK057", "PARK058", "PARK059", "PARK060",
    "PARK061", "PARK062", "PARK063", "PARK064", "PARK065",
    "PARK066", "PARK067", "PARK068", "PARK069", "PARK070",
    "PARK071", "PARK072", "PARK073", "PARK074", "PARK075",
    "PARK076", "PARK077", "PARK078", "PARK079", "PARK080",
    "PARK081", "PARK082", "PARK083", "PARK084", "PARK085",
    "PARK086", "PARK087", "PARK088", "PARK089", "PARK090",
    "PARK091", "PARK092", "PARK093", "PARK094", "PARK095",
    "PARK096", "PARK097", "PARK098", "PARK099", "PARK100"
]


vehicle_numbers = [
    "AB12 CDE", "AB13 CDE", "AB14 CDE", "AB15 CDE", "AB16 CDE",
    "AB17 CDE", "AB18 CDE", "AB19 CDE", "AB20 CDE", "AB21 CDE",
    "BC12 DEF", "BC13 DEF", "BC14 DEF", "BC15 DEF", "BC16 DEF",
    "BC17 DEF", "BC18 DEF", "BC19 DEF", "BC20 DEF", "BC21 DEF",
    "CD12 EFG", "CD13 EFG", "CD14 EFG", "CD15 EFG", "CD16 EFG",
    "CD17 EFG", "CD18 EFG", "CD19 EFG", "CD20 EFG", "CD21 EFG",
    "DE12 FGH", "DE13 FGH", "DE14 FGH", "DE15 FGH", "DE16 FGH",
    "DE17 FGH", "DE18 FGH", "DE19 FGH", "DE20 FGH", "DE21 FGH",
    "EF12 GHI", "EF13 GHI", "EF14 GHI", "EF15 GHI", "EF16 GHI",
    "EF17 GHI", "EF18 GHI", "EF19 GHI", "EF20 GHI", "EF21 GHI",
    "FG12 HIJ", "FG13 HIJ", "FG14 HIJ", "FG15 HIJ", "FG16 HIJ",
    "FG17 HIJ", "FG18 HIJ", "FG19 HIJ", "FG20 HIJ", "FG21 HIJ",
    "GH12 IJK", "GH13 IJK", "GH14 IJK", "GH15 IJK", "GH16 IJK",
    "GH17 IJK", "GH18 IJK", "GH19 IJK", "GH20 IJK", "GH21 IJK",
    "HJ12 KLM", "HJ13 KLM", "HJ14 KLM", "HJ15 KLM", "HJ16 KLM",
    "HJ17 KLM", "HJ18 KLM", "HJ19 KLM", "HJ20 KLM", "HJ21 KLM",
    "JK12 LMN", "JK13 LMN", "JK14 LMN", "JK15 LMN", "JK16 LMN",
    "JK17 LMN", "JK18 LMN", "JK19 LMN", "JK20 LMN", "JK21 LMN",
    "KL12 MNP", "KL13 MNP", "KL14 MNP", "KL15 MNP", "KL16 MNP",
    "KL17 MNP", "KL18 MNP", "KL19 MNP", "KL20 MNP", "KL21 MNP"
]

status = ["completed", "pending", "active", ""]

streets = [
    f"{i} High Street" for i in range(1, 101)
]

postcodes = [
    f"SW{i:1d} 1AA" for i in range(1, 10)
] + [
    f"E{i:2d} 1AA" for i in range(10, 101)
]

cities = [
    "London", "Manchester", "Birmingham", "Leeds", "Liverpool",
    "Bristol", "Sheffield", "Newcastle", "Nottingham", "Leicester"
]


latitudes = [
    51.5074, 51.5155, 51.5033, 51.5090, 51.5200,
    51.4988, 51.5120, 51.5065, 51.5180, 51.5010,
    51.4890, 51.4950, 51.5105, 51.5140, 51.5220,
    51.5080, 51.5160, 51.4995, 51.5045, 51.5190,
    51.4920, 51.5050, 51.5110, 51.5170, 51.5020,
    51.4970, 51.5130, 51.5210, 51.5060, 51.5000,
    51.4900, 51.4960, 51.5085, 51.5145, 51.5230,
    51.5095, 51.5150, 51.5015, 51.5070, 51.5185,
    51.4930, 51.5040, 51.5125, 51.5195, 51.5035,
    51.4980, 51.5100, 51.5165, 51.5055, 51.5205,
    51.4910, 51.4975, 51.5115, 51.5175, 51.5025,
    51.4990, 51.5135, 51.5225, 51.5068, 51.5005,
    51.4940, 51.5082, 51.5142, 51.5202, 51.5042,
    51.4965, 51.5102, 51.5162, 51.5012, 51.5182,
    51.4925, 51.5072, 51.5122, 51.5192, 51.5032,
    51.4985, 51.5152, 51.5212, 51.5052, 51.5002,
    51.4905, 51.5062, 51.5112, 51.5172, 51.5022,
    51.4972, 51.5092, 51.5148, 51.5208, 51.5048,
    51.4935, 51.5088, 51.5138, 51.5188, 51.5018,
    51.4955, 51.5108, 51.5168, 51.5228, 51.5068
]

longitudes = [
    -0.1278, -0.1419, -0.1195, -0.1350, -0.1020,
    -0.1740, -0.1250, -0.1500, -0.1100, -0.1400,
    -0.1600, -0.1300, -0.1450, -0.1150, -0.0950,
    -0.1350, -0.1050, -0.1550, -0.1200, -0.1000,
    -0.1700, -0.1250, -0.1450, -0.1100, -0.1300,
    -0.1500, -0.1200, -0.0900, -0.1400, -0.1600,
    -0.1800, -0.1350, -0.1150, -0.1000, -0.0850,
    -0.1450, -0.1250, -0.1550, -0.1300, -0.1050,
    -0.1650, -0.1200, -0.1400, -0.0950, -0.1350,
    -0.1500, -0.1100, -0.0900, -0.1450, -0.1000,
    -0.1750, -0.1300, -0.1550, -0.1150, -0.1400,
    -0.1600, -0.1250, -0.0850, -0.1350, -0.1500,
    -0.1700, -0.1200, -0.1000, -0.0900, -0.1450,
    -0.1350, -0.1100, -0.0950, -0.1550, -0.1050,
    -0.1650, -0.1300, -0.1450, -0.0850, -0.1400,
    -0.1500, -0.1150, -0.1000, -0.1350, -0.1600,
    -0.1800, -0.1250, -0.1550, -0.1100, -0.1450,
    -0.1350, -0.1200, -0.0950, -0.0850, -0.1500,
    -0.1700, -0.1150, -0.1400, -0.1000, -0.1300,
    -0.1550, -0.1250, -0.1050, -0.0900, -0.1450
]



NOW = datetime(2026, 10, 15, 12, 0)          # the "current time" of our fake data
TODAY = NOW.replace(hour=0, minute=0)

passwords = ['Pass@123', 'Secure#456', 'Park!789', 'Car$2026', 'Lot&Key01']
prices = [3.50, 4.20, 5.00, 5.80, 6.72, 7.50, 8.00]
statuses = ['completed', 'completed', 'completed', 'completed', 'pending', 'pending', 'active', 'cancelled']
start_hours = [6, 7, 8, 9, 10]               # every day of a reservation starts at this hour...
end_hours = [14, 15, 16, 17, 18]             # ...and ends at this hour
checkin_delays = [0, 2, 5, 6, 10, 15]        # minutes after start
checkout_delays = [-20, -10, 0, 5, 20]       # minutes around end


def to_text(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def overlaps(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


def generate_data():
    # one price per parking lot (needed to calculate costs)
    lot_prices = {}
    for pid in parking_lot_ids:
        lot_prices[pid] = random.choice(prices)

    users_list = []
    all_reservations = []         # every reservation (with user_id), used later for the admins
    reservation_number = 0
    session_number = 0

    # =============== USERS: 4 nested loops ===============
    # LOOP 1: users
    for i in range(80):
        email = normal_users_ids[i]
        name = users[20 + i]
        plate = vehicle_numbers[i]
        reservation_details = []
        used_times = []

        # LOOP 2: reservations of this user
        for _ in range(random.randint(3, 5)):
            status = random.choice(statuses)
            num_days = random.randint(1, 3)
            start_hour = random.choice(start_hours)
            end_hour = random.choice(end_hours)

            # first day of the reservation depends on the status
            if status == 'completed':
                first_day = TODAY - timedelta(days=random.randint(num_days, 20))   # all days in the past
            elif status == 'active':
                first_day = TODAY - timedelta(days=random.randint(0, num_days - 1))  # today is one of its days
            else:  # pending / cancelled
                first_day = TODAY + timedelta(days=random.randint(1, 10))

            start = first_day + timedelta(hours=start_hour)
            end = first_day + timedelta(days=num_days - 1, hours=end_hour)

            # same car can't have two reservations at the same time
            clash = False
            for old_start, old_end in used_times:
                if overlaps(start, end, old_start, old_end):
                    clash = True
            if clash:
                continue
            used_times.append((start, end))

            reservation_number += 1
            parking_id = random.choice(parking_lot_ids)
            created = start - timedelta(days=random.randint(1, 7), hours=random.randint(0, 12))

            sessions = []     # stays empty for pending and cancelled

            if status == 'completed' or status == 'active':
                # LOOP 3: sessions (one per day)
                for d in range(num_days):
                    day = first_day + timedelta(days=d)
                    if day > TODAY:
                        break                      # future days: no session yet

                    session_number += 1
                    is_open = (status == 'active' and day == TODAY)   # car is still inside today
                    if is_open:
                        how_many = 1
                    else:
                        how_many = random.randint(1, 2)

                    movements = []
                    total_hours = 0

                    # LOOP 4: movements (check-in / check-out)
                    for m in range(how_many):
                        if how_many == 1:                      # stays all day
                            check_in = day + timedelta(hours=start_hour, minutes=random.choice(checkin_delays))
                            check_out = day + timedelta(hours=end_hour, minutes=random.choice(checkout_delays))
                        elif m == 0:                           # morning, leaves at 12:00
                            check_in = day + timedelta(hours=start_hour, minutes=random.choice(checkin_delays))
                            check_out = day + timedelta(hours=12)
                        else:                                  # comes back at 13:00
                            check_in = day + timedelta(hours=13)
                            check_out = day + timedelta(hours=end_hour, minutes=random.choice(checkout_delays))

                        if is_open:
                            check_out = None               # still inside
                        else:
                            total_hours += (check_out - check_in).total_seconds() / 3600

                        movements.append({
                            "check_in_time": to_text(check_in),
                            "check_out_time": to_text(check_out)
                        })

                    # cost of the session = hours inside * price of this lot
                    if is_open:
                        cost = None
                    else:
                        cost = round(total_hours * lot_prices[parking_id], 2)

                    sessions.append({
                        "session_id": "S" + str(session_number).zfill(6),
                        "total_cost": cost,
                        "movements": movements
                    })

            reservation = {
                "reservation_id": "R" + str(reservation_number).zfill(6),
                "parking_id": parking_id,
                "vehicle_number": plate,
                "start_time": to_text(start),
                "end_time": to_text(end),
                "status": status,
                "created_at": to_text(created),
                "sessions": sessions
            }
            reservation_details.append(reservation)

            # keep a copy (with user_id and parking_id) for the admins
            copy = dict(reservation)
            copy["user_id"] = email
            all_reservations.append(copy)

        users_list.append({
            "role": "user",
            "user_id": email,
            "name": name,
            "password_hash": hashlib.sha256(random.choice(passwords).encode()).hexdigest(),
            "reservation_details": reservation_details
        })

    # =============== ADMINS: 5 nested loops ===============
    # LOOP 1: admins
    for i in range(20):
        my_lots = parking_lot_ids[i * 5: i * 5 + 5]       # admin 0 -> lots 0-4, admin 1 -> lots 5-9 ...
        managed_parking_lots = []

        # LOOP 2: lots of this admin
        for pid in my_lots:
            reservation_refs = []

            # LOOP 3: reservations of this lot (taken from the users' reservations)
            for r in all_reservations:
                if r["parking_id"] != pid:
                    continue
                ref_sessions = []

                # LOOP 4: sessions of this reservation
                for s in r["sessions"]:
                    ref_movements = []

                    # LOOP 5: movements of this session
                    for m in s["movements"]:
                        ref_movements.append({
                            "check_in_time": m["check_in_time"],
                            "check_out_time": m["check_out_time"]
                        })

                    ref_sessions.append({
                        "session_id": s["session_id"],
                        "total_cost": s["total_cost"],
                        "movements": ref_movements
                    })

                reservation_refs.append({
                    "reservation_id": r["reservation_id"],
                    "user_id": r["user_id"],
                    "vehicle_number": r["vehicle_number"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "start_time": r["start_time"],
                    "end_time": r["end_time"],
                    "sessions": ref_sessions
                })

            managed_parking_lots.append({
                "parking_id": pid,
                "reservation_refs": reservation_refs
            })

        users_list.append({
            "role": "admin",
            "user_id": admins_ids[i],
            "name": users[i],
            "password_hash": hashlib.sha256(random.choice(passwords).encode()).hexdigest(),
            "managed_parking_lots": managed_parking_lots
        })

    return users_list, all_reservations, lot_prices


users_list, all_reservations, lot_prices = generate_data()

with open('users_raw.json', 'w') as fout:
    json.dump(users_list, fout, indent=4)

# saved for the parking_lots file, so both files match
with open('reservations_flat.json', 'w') as fout:
    json.dump(all_reservations, fout, indent=4)
with open('lot_prices.json', 'w') as fout:
    json.dump(lot_prices, fout, indent=4)