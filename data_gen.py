import random
import json
import hashlib
from datetime import datetime, timedelta

random.seed(42)

# 30 admins + 70 normal users = 100 users
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

admins_ids = [f"admin.{name.lower()}@example.com" for name in users[:30]]
normal_users_ids = [f"{name.lower()}@example.com" for name in users[30:]]
parking_lot_ids = [f"P{i:04d}" for i in range(1, 101)]

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

streets = [
    f"{i} High Street" for i in range(1, 101)
]

districts = ["SW1", "SW3", "SW7", "W1", "W2", "WC1", "WC2", "EC1", "EC2", "E1", "E2", "SE1", "N1", "NW1"]
postcodes = [f"{districts[i % len(districts)]} {1 + i // len(districts)}AA" for i in range(100)]

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


# Demo current time
NOW = datetime(2026, 10, 15, 12, 0)          
TODAY = NOW.replace(hour=0, minute=0)

passwords = ['Pass@123', 'Secure#456', 'Park!789', 'Car$2026', 'Lot&Key01']
statuses = ['completed', 'pending', 'active', 'cancelled']
start_hours = [6, 7, 8, 9, 10]               # every day of a reservation starts at this hour
end_hours = [14, 15, 16, 17, 18]             # ends at this hour
checkin_delays = [0, 2, 5, 6, 10, 15]        # minutes after start
checkout_delays = [-20, -10, 0, 5, 20]       # minutes around end


def to_text(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")




# PARKING LOTS (price, spaces and admins)
def create_parking_lots():
    parking_lots = []
    
    for i in range(100):
        parking_lots.append({
            "parking_id": parking_lot_ids[i],
            "address": {
                "street": streets[i],
                "city": "London",
                "postcode": postcodes[i]
            },
            "location": {
                "type": "Point",
                "coordinates": [longitudes[i], latitudes[i]]
            },
            "total_spaces": random.randint(6, 30),
            "num_available_spaces": None,          # filled in at the end
            "updated_at": to_text(NOW),
            "price_per_hour": round(random.uniform(2.5, 9.0), 2),
            "administrators": [],                  # filled in by assign_admins
            "reservations": [],                    # filled in by generate_users
            "income": None,                        # filled in at the end
            "availability_history": []             # filled in at the end
        })
        
    return parking_lots





def assign_admins(parking_lots):

    admin_lots = {admin_id: [] for admin_id in admins_ids}

    #Link admins to each lot
    def link(lot, i):
        lot["administrators"].append({"user_id": admins_ids[i], "name": users[i]})
        admin_lots[admins_ids[i]].append(lot)

    # first admin of every lot (spread evenly, so every admin gets at least 1 lot)
    for n, lot in enumerate(parking_lots):
        link(lot, n % 30)

    # 0, 1 or 2 extra admins per lot, only if that admin has less lots (for this dataset I used 5)
    for lot in parking_lots:
        extra = random.choices([0, 1, 2], [60, 30, 10])[0]
        taken = [admin["user_id"] for admin in lot["administrators"]]
        free = [i for i in range(30) if admins_ids[i] not in taken and len(admin_lots[admins_ids[i]]) < 5]
        for i in random.sample(free, min(extra, len(free))):
            link(lot, i)

    return admin_lots












# USERS

def generate_users(parking_lots):
    users_list = []
    reservation_number = 0
    session_number = 0
    
    

    # USERS: 4 nested loops 
    
    
    
    # LOOP 1: users
    for i in range(70):
        email = normal_users_ids[i]
        name = users[30 + i]
        plate = vehicle_numbers[i]
        reservation_details = []
        user_statuses = []

        # LOOP 2: reservations of this user (I kept it up to 5 for this dataset)
        for slot in range(random.randint(0, 5)):
            status = random.choice(statuses)
            
            # active and pending can happen only once for each user
            if status in ('active', 'pending') and status in user_statuses:
                status = random.choice(['completed', 'cancelled'])
                
            user_statuses.append(status)

            num_days = random.randint(1, 3)
            start_hour = random.choice(start_hours)
            end_hour = random.choice(end_hours)

            # every reservation has its own 5-day slot, so the same car never has two at the same time
            if status == 'completed':
                first_day = TODAY - timedelta(days=5 * (slot + 1))                  # all days in the past
            elif status == 'active':
                first_day = TODAY - timedelta(days=random.randint(0, num_days - 1))  # today is one of its days
            else:  # pending / cancelled
                first_day = TODAY + timedelta(days=5 * (slot + 1))

            start = first_day + timedelta(hours=start_hour)
            end = first_day + timedelta(days=num_days - 1, hours=end_hour)

            # choose a parking lot that is not full of reservations yet
            lot = random.choice([l for l in parking_lots if len(l["reservations"]) < l["total_spaces"]])
            parking_id = lot["parking_id"]
            created = start - timedelta(days=random.randint(1, 7), hours=random.randint(0, 12))

            reservation_number += 1
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

                    # cost of the session = hours inside * price_per_hour of this lot
                    if is_open:
                        cost = None
                    else:
                        cost = round(total_hours * lot["price_per_hour"], 2)

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

            # the parking lot keeps its own copy of the reservation (with user_id)
            lot_copy = dict(reservation)
            lot_copy["user_id"] = email
            lot["reservations"].append(lot_copy)

        users_list.append({
            "role": "user",
            "user_id": email,
            "name": name,
            "password_hash": hashlib.sha256(random.choice(passwords).encode()).hexdigest(),
            "reservation_details": reservation_details
        })

    return users_list











# PARKING LOTS (last part: availability and income)









def vehicles_inside_at(lot, timestamp):
    vehicles = []
    for reservation in lot["reservations"]:
        for session in reservation["sessions"]:
            for movement in session["movements"]:
                check_in = movement["check_in_time"]
                check_out = movement["check_out_time"]
                if check_in <= timestamp and (check_out is None or check_out > timestamp):
                    vehicles.append({
                        "reservation_id": reservation["reservation_id"],
                        "vehicle_number": reservation["vehicle_number"]
                    })
    return vehicles


def finish_parking_lots(parking_lots):
    for lot in parking_lots:
        # availability history: six hours ago and now
        for hours_ago in [6, 0]:
            history_timestamp = to_text(NOW - timedelta(hours=hours_ago))
            inside = vehicles_inside_at(lot, history_timestamp)
            lot["availability_history"].append({
                "updated_at": history_timestamp,
                "num_available_spaces": lot["total_spaces"] - len(inside),
                "vehicles_inside": inside
            })
        lot["num_available_spaces"] = lot["availability_history"][-1]["num_available_spaces"]

        # income from completed reservations only
        total_income = 0.0
        completed_reservations = 0
        for reservation in lot["reservations"]:
            if reservation["status"] == "completed":
                completed_reservations += 1
                for session in reservation["sessions"]:
                    total_income += session["total_cost"]

        lot["income"] = {
            "total_income": round(total_income, 2),
            "completed_reservations": completed_reservations,
            "updated_at": to_text(NOW)
        }



# ADMINS
def generate_admins(admin_lots):
    admins_list = []



    #  ADMINS 
    
    
    
    
    # LOOP 1: admins
    for i in range(30):
        managed_parking_lots = []

        # LOOP 2: lots of this admin (1 to 5)
        for lot in admin_lots[admins_ids[i]]:
            managed_parking_lots.append({
                "parking_id": lot["parking_id"],
                "reservation_refs": lot["reservations"]     # the reservations of that lot (many users)
            })

        admins_list.append({
            "role": "admin",
            "user_id": admins_ids[i],
            "name": users[i],
            "password_hash": hashlib.sha256(random.choice(passwords).encode()).hexdigest(),
            "managed_parking_lots": managed_parking_lots
        })

    return admins_list




# Generate the dataset and save in json files
parking_lots = create_parking_lots()
admin_lots = assign_admins(parking_lots)
users_list = generate_users(parking_lots)
finish_parking_lots(parking_lots)
admins_list = generate_admins(admin_lots)

with open("users.json", "w", encoding="utf-8") as fout:
    json.dump(users_list + admins_list, fout, indent=4)

with open("parking_lots.json", "w", encoding="utf-8") as fout:
    json.dump(parking_lots, fout, indent=4)

