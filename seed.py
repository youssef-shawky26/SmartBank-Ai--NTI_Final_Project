import random
from werkzeug.security import generate_password_hash
import db

random.seed(7)


def seed_if_empty():
    conn = db.get_db()
    cur = conn.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] > 0:
        conn.close()
        return

    now = db.now()

    conn.execute(
        """INSERT INTO users (username, password_hash, role, full_name, age, gender, phone, email,
           state, job, account_number, balance, income, employment_years, home_ownership,
           credit_score, credit_history_years, has_prior_default, geography, tenure_years,
           num_of_products, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("manager", generate_password_hash("manager123"), "manager", "Dana Whitfield", 41, "female",
         "555-0100", "dana.whitfield@Verdict.demo", "NY", "Bank manager",
         "AUR-1000-0000", 0, None, None, None, None, None, "No", "France", None, None, now),
    )

    # Diverse demo clients shaped like rows from loan_data / churn training distributions.
    # Only these seeded accounts start with predefined balances.
    demo_clients = [
        dict(username="jmartin", password="client123", full_name="Jordan Martin", age=29, gender="male",
             phone="555-0142", email="jordan.martin@example.com", state="CA", job="Software engineer",
             balance=18450.32, income=98000, employment_years=5, home_ownership="RENT",
             credit_score=712, credit_history_years=6, has_prior_default="No",
             geography="France", tenure_years=3, num_of_products=2),
        dict(username="sfields", password="client123", full_name="Sasha Fields", age=52, gender="female",
             phone="555-0173", email="sasha.fields@example.com", state="TX", job="Physician",
             balance=142870.10, income=210000, employment_years=18, home_ownership="MORTGAGE",
             credit_score=799, credit_history_years=22, has_prior_default="No",
             geography="Germany", tenure_years=11, num_of_products=1),
        dict(username="rkline", password="client123", full_name="Riley Kline", age=23, gender="female",
             phone="555-0118", email="riley.kline@example.com", state="OH", job="Barista",
             balance=612.44, income=27000, employment_years=1, home_ownership="RENT",
             credit_score=581, credit_history_years=1, has_prior_default="Yes",
             geography="Spain", tenure_years=1, num_of_products=1),
        dict(username="achen", password="client123", full_name="Avery Chen", age=34, gender="female",
             phone="555-0201", email="avery.chen@example.com", state="NY", job="Marketing manager",
             balance=32400.00, income=87500, employment_years=8, home_ownership="RENT",
             credit_score=688, credit_history_years=9, has_prior_default="No",
             geography="France", tenure_years=5, num_of_products=2),
        dict(username="dokafor", password="client123", full_name="Dele Okafor", age=41, gender="male",
             phone="555-0202", email="dele.okafor@example.com", state="GA", job="Accountant",
             balance=56120.75, income=112000, employment_years=14, home_ownership="MORTGAGE",
             credit_score=741, credit_history_years=16, has_prior_default="No",
             geography="Germany", tenure_years=8, num_of_products=3),
        dict(username="mrossi", password="client123", full_name="Marco Rossi", age=27, gender="male",
             phone="555-0203", email="marco.rossi@example.com", state="FL", job="Retail associate",
             balance=2180.50, income=38500, employment_years=3, home_ownership="RENT",
             credit_score=602, credit_history_years=3, has_prior_default="No",
             geography="Spain", tenure_years=2, num_of_products=1),
        dict(username="lpatel", password="client123", full_name="Lila Patel", age=48, gender="female",
             phone="555-0204", email="lila.patel@example.com", state="IL", job="University professor",
             balance=89200.00, income=145000, employment_years=20, home_ownership="OWN",
             credit_score=810, credit_history_years=24, has_prior_default="No",
             geography="France", tenure_years=14, num_of_products=2),
        dict(username="tbrooks", password="client123", full_name="Tyler Brooks", age=31, gender="male",
             phone="555-0205", email="tyler.brooks@example.com", state="WA", job="Uber driver",
             balance=940.15, income=32000, employment_years=2, home_ownership="RENT",
             credit_score=548, credit_history_years=2, has_prior_default="Yes",
             geography="Spain", tenure_years=1, num_of_products=1),
        dict(username="nkim", password="client123", full_name="Nina Kim", age=38, gender="female",
             phone="555-0206", email="nina.kim@example.com", state="NJ", job="Nurse practitioner",
             balance=47850.00, income=118000, employment_years=11, home_ownership="MORTGAGE",
             credit_score=765, credit_history_years=12, has_prior_default="No",
             geography="Germany", tenure_years=7, num_of_products=2),
        dict(username="jhernandez", password="client123", full_name="Javier Hernandez", age=55, gender="male",
             phone="555-0207", email="javier.hernandez@example.com", state="AZ", job="Construction supervisor",
             balance=15670.40, income=64000, employment_years=25, home_ownership="OWN",
             credit_score=670, credit_history_years=18, has_prior_default="No",
             geography="France", tenure_years=10, num_of_products=1),
        dict(username="ewong", password="client123", full_name="Elena Wong", age=26, gender="female",
             phone="555-0208", email="elena.wong@example.com", state="MA", job="Graduate student",
             balance=1250.00, income=22000, employment_years=0, home_ownership="RENT",
             credit_score=615, credit_history_years=1, has_prior_default="No",
             geography="Spain", tenure_years=1, num_of_products=1),
        dict(username="cbrown", password="client123", full_name="Caleb Brown", age=44, gender="male",
             phone="555-0209", email="caleb.brown@example.com", state="CO", job="IT consultant",
             balance=67500.00, income=132000, employment_years=16, home_ownership="MORTGAGE",
             credit_score=728, credit_history_years=15, has_prior_default="No",
             geography="Germany", tenure_years=9, num_of_products=3),
    ]
    for i, c in enumerate(demo_clients):
        conn.execute(
            """INSERT INTO users (username, password_hash, role, full_name, age, gender, phone, email,
               state, job, account_number, balance, income, employment_years, home_ownership,
               credit_score, credit_history_years, has_prior_default, geography, tenure_years,
               num_of_products, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (c["username"], generate_password_hash(c["password"]), "client", c["full_name"], c["age"],
             c["gender"], c["phone"], c["email"], c["state"], c["job"],
             f"AUR-{1001+i}-{random.randint(1000,9999)}", c["balance"], c["income"],
             c["employment_years"], c["home_ownership"], c["credit_score"], c["credit_history_years"],
             c["has_prior_default"], c["geography"], c["tenure_years"], c["num_of_products"], now),
        )

    # --- real EUR/USD history from currency.csv (the same data the model was trained on) ---
    import csv
    with open("reference_data/currency.csv", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            conn.execute(
                "INSERT INTO currency_history (pair, day_index, close_price) VALUES (?,?,?)",
                ("EUR/USD", i, float(row["Rate"])),
            )

    conn.commit()
    conn.close()
    print(
        "Seed data created: manager/manager123 + demo clients "
        "(jmartin, sfields, rkline, achen, dokafor, mrossi, lpatel, tbrooks, nkim, jhernandez, ewong, cbrown) "
        "/ client123"
    )
