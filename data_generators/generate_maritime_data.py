"""
Maritime Lakehouse Platform
Script de generation des donnees synthetiques
Target : YOUSSOUF\MICROSOFTSQLSERV -> MaritimeDB
"""

import pyodbc
import random
from datetime import datetime, timedelta
from faker import Faker
from tqdm import tqdm

fake = Faker()
random.seed(42)

CONN_MASTER = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=YOUSSOUF\\MICROSOFTSQLSERV;"
    "DATABASE=master;"
    "Trusted_Connection=yes;"
)

CONN_MARITIME = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=YOUSSOUF\\MICROSOFTSQLSERV;"
    "DATABASE=MaritimeDB;"
    "Trusted_Connection=yes;"
)

def get_master():
    conn = pyodbc.connect(CONN_MASTER)
    conn.autocommit = True
    return conn

def get_conn():
    return pyodbc.connect(CONN_MARITIME)

def last_id(cursor):
    cursor.execute("SELECT @@IDENTITY")
    return int(cursor.fetchone()[0])

def create_database():
    print("\n[1/3] Creation de MaritimeDB...")
    conn = get_master()
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (
            SELECT name FROM sys.databases WHERE name = 'MaritimeDB'
        )
        CREATE DATABASE MaritimeDB
    """)
    conn.close()
    print("  OK - MaritimeDB creee")

def create_tables():
    print("\n[2/3] Creation des tables...")
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='vessel_classes')
    CREATE TABLE vessel_classes (
        class_id         INT IDENTITY(1,1) PRIMARY KEY,
        class_name       NVARCHAR(100) NOT NULL,
        vessel_type      NVARCHAR(50)  NOT NULL,
        max_dwt          DECIMAL(12,2),
        max_teu          INT,
        avg_speed_knots  DECIMAL(5,2),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='vessels')
    CREATE TABLE vessels (
        vessel_id        INT IDENTITY(1,1) PRIMARY KEY,
        imo_number       CHAR(7)       NOT NULL UNIQUE,
        vessel_name      NVARCHAR(100) NOT NULL,
        class_id         INT REFERENCES vessel_classes(class_id),
        flag_country     NVARCHAR(50)  NOT NULL,
        build_year       INT,
        deadweight_tons  DECIMAL(12,2),
        teu_capacity     INT,
        gross_tonnage    DECIMAL(12,2),
        status           NVARCHAR(20)  DEFAULT 'Active',
        owner_company    NVARCHAR(100),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ports')
    CREATE TABLE ports (
        port_id          INT IDENTITY(1,1) PRIMARY KEY,
        port_code        CHAR(5)       NOT NULL UNIQUE,
        port_name        NVARCHAR(100) NOT NULL,
        country          NVARCHAR(50)  NOT NULL,
        region           NVARCHAR(50)  NOT NULL,
        latitude         DECIMAL(9,6)  NOT NULL,
        longitude        DECIMAL(9,6)  NOT NULL,
        port_type        NVARCHAR(50)  NOT NULL,
        max_vessel_dwt   DECIMAL(12,2),
        timezone         NVARCHAR(50),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='terminals')
    CREATE TABLE terminals (
        terminal_id      INT IDENTITY(1,1) PRIMARY KEY,
        port_id          INT REFERENCES ports(port_id),
        terminal_name    NVARCHAR(100) NOT NULL,
        terminal_type    NVARCHAR(50)  NOT NULL,
        berth_count      INT,
        max_depth_m      DECIMAL(5,2),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='berths')
    CREATE TABLE berths (
        berth_id         INT IDENTITY(1,1) PRIMARY KEY,
        terminal_id      INT REFERENCES terminals(terminal_id),
        berth_name       NVARCHAR(50)  NOT NULL,
        length_m         DECIMAL(7,2),
        depth_m          DECIMAL(5,2),
        berth_type       NVARCHAR(50),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='voyages')
    CREATE TABLE voyages (
        voyage_id            INT IDENTITY(1,1) PRIMARY KEY,
        voyage_code          NVARCHAR(20)  NOT NULL UNIQUE,
        vessel_id            INT REFERENCES vessels(vessel_id),
        origin_port_id       INT REFERENCES ports(port_id),
        destination_port_id  INT REFERENCES ports(port_id),
        etd                  DATETIME2 NOT NULL,
        atd                  DATETIME2,
        eta                  DATETIME2 NOT NULL,
        ata                  DATETIME2,
        distance_nm          DECIMAL(10,2),
        voyage_status        NVARCHAR(20) DEFAULT 'Planned',
        created_at           DATETIME2 DEFAULT GETDATE(),
        updated_at           DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='port_calls')
    CREATE TABLE port_calls (
        port_call_id     INT IDENTITY(1,1) PRIMARY KEY,
        voyage_id        INT REFERENCES voyages(voyage_id),
        port_id          INT REFERENCES ports(port_id),
        berth_id         INT REFERENCES berths(berth_id),
        eta              DATETIME2 NOT NULL,
        ata              DATETIME2,
        etd              DATETIME2 NOT NULL,
        atd              DATETIME2,
        call_purpose     NVARCHAR(50),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cargo_types')
    CREATE TABLE cargo_types (
        cargo_type_id    INT IDENTITY(1,1) PRIMARY KEY,
        type_code        NVARCHAR(10)  NOT NULL UNIQUE,
        type_name        NVARCHAR(50)  NOT NULL,
        category         NVARCHAR(50)  NOT NULL,
        hazmat_class     NVARCHAR(10),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cargo_orders')
    CREATE TABLE cargo_orders (
        order_id         INT IDENTITY(1,1) PRIMARY KEY,
        order_code       NVARCHAR(20)  NOT NULL UNIQUE,
        client_name      NVARCHAR(100) NOT NULL,
        cargo_type_id    INT REFERENCES cargo_types(cargo_type_id),
        voyage_id        INT REFERENCES voyages(voyage_id),
        tonnage          DECIMAL(12,2) NOT NULL,
        volume_m3        DECIMAL(12,2),
        freight_rate     DECIMAL(10,2),
        order_status     NVARCHAR(20) DEFAULT 'Confirmed',
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cargo_manifests')
    CREATE TABLE cargo_manifests (
        manifest_id       INT IDENTITY(1,1) PRIMARY KEY,
        order_id          INT REFERENCES cargo_orders(order_id),
        manifest_code     NVARCHAR(20)  NOT NULL UNIQUE,
        load_port_id      INT REFERENCES ports(port_id),
        discharge_port_id INT REFERENCES ports(port_id),
        actual_tonnage    DECIMAL(12,2),
        declared_value    DECIMAL(15,2),
        customs_status    NVARCHAR(20) DEFAULT 'Pending',
        created_at        DATETIME2 DEFAULT GETDATE(),
        updated_at        DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='clients')
    CREATE TABLE clients (
        client_id        INT IDENTITY(1,1) PRIMARY KEY,
        client_code      NVARCHAR(10)  NOT NULL UNIQUE,
        company_name     NVARCHAR(100) NOT NULL,
        country          NVARCHAR(50)  NOT NULL,
        segment          NVARCHAR(50),
        credit_limit     DECIMAL(15,2),
        payment_terms    INT DEFAULT 30,
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='contracts')
    CREATE TABLE contracts (
        contract_id      INT IDENTITY(1,1) PRIMARY KEY,
        contract_code    NVARCHAR(20)  NOT NULL UNIQUE,
        client_id        INT REFERENCES clients(client_id),
        vessel_id        INT REFERENCES vessels(vessel_id),
        start_date       DATE NOT NULL,
        end_date         DATE NOT NULL,
        contract_type    NVARCHAR(50),
        base_rate        DECIMAL(10,2),
        currency         CHAR(3) DEFAULT 'USD',
        contract_status  NVARCHAR(20) DEFAULT 'Active',
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='seafarers')
    CREATE TABLE seafarers (
        seafarer_id      INT IDENTITY(1,1) PRIMARY KEY,
        seafarer_code    NVARCHAR(10)  NOT NULL UNIQUE,
        full_name        NVARCHAR(100) NOT NULL,
        nationality      NVARCHAR(50)  NOT NULL,
        rank_title       NVARCHAR(50)  NOT NULL,
        date_of_birth    DATE,
        stcw_number      NVARCHAR(20),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='crew_assignments')
    CREATE TABLE crew_assignments (
        assignment_id    INT IDENTITY(1,1) PRIMARY KEY,
        seafarer_id      INT REFERENCES seafarers(seafarer_id),
        vessel_id        INT REFERENCES vessels(vessel_id),
        voyage_id        INT REFERENCES voyages(voyage_id),
        embark_date      DATE NOT NULL,
        disembark_date   DATE,
        role_onboard     NVARCHAR(50) NOT NULL,
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='fuel_grades')
    CREATE TABLE fuel_grades (
        fuel_grade_id    INT IDENTITY(1,1) PRIMARY KEY,
        grade_code       NVARCHAR(10)  NOT NULL UNIQUE,
        grade_name       NVARCHAR(50)  NOT NULL,
        sulfur_content   DECIMAL(5,3),
        imo_compliant    BIT DEFAULT 1,
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='bunkering_events')
    CREATE TABLE bunkering_events (
        bunker_id        INT IDENTITY(1,1) PRIMARY KEY,
        vessel_id        INT REFERENCES vessels(vessel_id),
        port_id          INT REFERENCES ports(port_id),
        fuel_grade_id    INT REFERENCES fuel_grades(fuel_grade_id),
        bunker_date      DATE NOT NULL,
        quantity_mt      DECIMAL(10,2) NOT NULL,
        unit_price_usd   DECIMAL(10,2) NOT NULL,
        total_cost_usd   DECIMAL(15,2) NOT NULL,
        supplier_name    NVARCHAR(100),
        created_at       DATETIME2 DEFAULT GETDATE(),
        updated_at       DATETIME2 DEFAULT GETDATE()
    )""")

    conn.commit()
    conn.close()
    print("  OK - Toutes les tables creees")

def populate_data():
    print("\n[3/3] Insertion des donnees...")
    conn = get_conn()
    cursor = conn.cursor()

    # VESSEL CLASSES
    print("  3.1 Vessel classes...")
    classes = [
        ("Handysize",   "Bulk Carrier",  35000, None,  13.5),
        ("Handymax",    "Bulk Carrier",  58000, None,  14.0),
        ("Panamax",     "Bulk Carrier",  80000, None,  14.5),
        ("Capesize",    "Bulk Carrier", 180000, None,  15.0),
        ("Feeder",      "Container",      8000,  800,  16.0),
        ("Panamax Box", "Container",     65000, 5000,  22.0),
        ("VLCC",        "Tanker",       320000, None,  15.5),
        ("Suezmax",     "Tanker",       160000, None,  15.0),
        ("RORO",        "RoRo",          25000, None,  18.0),
        ("LNG Carrier", "LNG",           80000, None,  19.5),
    ]
    for c in classes:
        cursor.execute("""
            INSERT INTO vessel_classes
            (class_name,vessel_type,max_dwt,max_teu,avg_speed_knots)
            VALUES (?,?,?,?,?)
        """, c)
    conn.commit()
    cursor.execute("SELECT class_id,max_dwt,max_teu FROM vessel_classes")
    class_rows = cursor.fetchall()
    print("  OK")

    # PORTS
    print("  3.2 Ports mondiaux...")
    ports = [
        ("CAMON","Montreal",        "Canada",       "North America",  45.5017, -73.5673,"Container/Bulk", 60000,"America/Toronto"),
        ("CAVAN","Vancouver",       "Canada",       "North America",  49.2827,-123.1207,"Container/Bulk",200000,"America/Vancouver"),
        ("USNYC","New York",        "USA",          "North America",  40.7128, -74.0060,"Container",     150000,"America/New_York"),
        ("USHOU","Houston",         "USA",          "North America",  29.7604, -95.3698,"Tanker/Bulk",   200000,"America/Chicago"),
        ("NLRTM","Rotterdam",       "Netherlands",  "Europe",         51.9225,   4.4792,"Container/Bulk",350000,"Europe/Amsterdam"),
        ("DEHAM","Hamburg",         "Germany",      "Europe",         53.5753,   9.9000,"Container",     250000,"Europe/Berlin"),
        ("GBFXT","Felixstowe",      "UK",           "Europe",         51.9600,   1.3500,"Container",     200000,"Europe/London"),
        ("CNSHA","Shanghai",        "China",        "Asia Pacific",   31.2304, 121.4737,"Container",     400000,"Asia/Shanghai"),
        ("CNNGB","Ningbo",          "China",        "Asia Pacific",   29.8683, 121.5440,"Container/Bulk",350000,"Asia/Shanghai"),
        ("SGSIN","Singapore",       "Singapore",    "Asia Pacific",    1.3521, 103.8198,"Container/Tanker",400000,"Asia/Singapore"),
        ("JPYOK","Yokohama",        "Japan",        "Asia Pacific",   35.4437, 139.6380,"Container",     200000,"Asia/Tokyo"),
        ("AEDXB","Dubai Jebel Ali", "UAE",          "Middle East",    25.0000,  55.1000,"Container",     250000,"Asia/Dubai"),
        ("EGPSD","Port Said",       "Egypt",        "Africa",         31.2652,  32.3018,"Container/Tanker",150000,"Africa/Cairo"),
        ("ZACPT","Cape Town",       "South Africa", "Africa",        -33.9249,  18.4241,"Bulk",           80000,"Africa/Johannesburg"),
        ("BRSSZ","Santos",          "Brazil",       "South America", -23.9618, -46.3322,"Container/Bulk",200000,"America/Sao_Paulo"),
        ("AUMEL","Melbourne",       "Australia",    "Oceania",       -37.8136, 144.9631,"Container",     120000,"Australia/Melbourne"),
        ("KRPUS","Busan",           "South Korea",  "Asia Pacific",   35.1028, 129.0403,"Container",     300000,"Asia/Seoul"),
        ("INBOM","Mumbai",          "India",        "Asia Pacific",   19.0760,  72.8777,"Container/Tanker",200000,"Asia/Kolkata"),
        ("CLVAP","Valparaiso",      "Chile",        "South America", -33.0472, -71.6127,"Container",      80000,"America/Santiago"),
        ("MAPTM","Tanger Med",      "Morocco",      "Africa",         35.8833,  -5.5000,"Container",     200000,"Africa/Casablanca"),
    ]
    for p in ports:
        cursor.execute("""
            INSERT INTO ports
            (port_code,port_name,country,region,
             latitude,longitude,port_type,max_vessel_dwt,timezone)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, p)
    conn.commit()
    cursor.execute("SELECT port_id FROM ports")
    port_ids = [r[0] for r in cursor.fetchall()]
    print("  OK")

    # FUEL GRADES
    print("  3.3 Fuel grades...")
    grades = [
        ("HFO",   "Heavy Fuel Oil",          3.500, 0),
        ("VLSFO", "Very Low Sulfur Fuel Oil", 0.500, 1),
        ("MGO",   "Marine Gas Oil",           0.100, 1),
        ("LNG",   "Liquefied Natural Gas",    0.000, 1),
        ("LSMGO", "Low Sulfur MGO",           0.100, 1),
    ]
    for g in grades:
        cursor.execute("""
            INSERT INTO fuel_grades
            (grade_code,grade_name,sulfur_content,imo_compliant)
            VALUES (?,?,?,?)
        """, g)
    conn.commit()
    cursor.execute("SELECT fuel_grade_id FROM fuel_grades")
    fuel_ids = [r[0] for r in cursor.fetchall()]
    print("  OK")

    # CARGO TYPES
    print("  3.4 Cargo types...")
    ctypes = [
        ("GRAIN", "Grain",       "Dry Bulk",    None),
        ("COAL",  "Coal",        "Dry Bulk",    None),
        ("IRON",  "Iron Ore",    "Dry Bulk",    None),
        ("FERT",  "Fertilizers", "Dry Bulk",    None),
        ("CONT",  "Containers",  "Container",   None),
        ("CRUDE", "Crude Oil",   "Liquid Bulk", "III"),
        ("CHEM",  "Chemicals",   "Liquid Bulk", "II"),
        ("LNG_C", "LNG",         "Gas",         "II G"),
        ("RORO_C","RoRo Cargo",  "RoRo",        None),
        ("REFER", "Refrigerated","Reefer",       None),
    ]
    for ct in ctypes:
        cursor.execute("""
            INSERT INTO cargo_types
            (type_code,type_name,category,hazmat_class)
            VALUES (?,?,?,?)
        """, ct)
    conn.commit()
    cursor.execute("SELECT cargo_type_id FROM cargo_types")
    cargo_type_ids = [r[0] for r in cursor.fetchall()]
    print("  OK")

    # VESSELS
    print("  3.5 150 vessels...")
    flags = ["Panama","Marshall Islands","Liberia","Bahamas",
             "Malta","Cyprus","Greece","Singapore","Norway","Japan"]
    owners = ["Pacific Maritime Ltd","Atlantic Shipping Corp",
              "Global Ocean Lines","Nordic Carriers",
              "Eastern Pacific Shipping","Trans-Atlantic Freight",
              "Maritime Solutions Inc","Deep Sea Transport",
              "Ocean Bridge Logistics","Arctic Marine"]
    suffixes = ["Star","Spirit","Express","Pioneer","Horizon",
                "Venture","Eagle","Navigator","Mariner","Pacific"]
    vessel_ids = []
    used_imos = set()
    for i in tqdm(range(150)):
        while True:
            imo = str(random.randint(1000000,9999999))
            if imo not in used_imos:
                used_imos.add(imo)
                break
        row = random.choice(class_rows)
        class_id, max_dwt, max_teu = row[0], row[1], row[2]
        dwt = round(random.uniform(float(max_dwt)*0.7, float(max_dwt)), 2) if max_dwt else None
        teu = random.randint(int(max_teu*0.7), max_teu) if max_teu else None
        cursor.execute("""
            INSERT INTO vessels
            (imo_number,vessel_name,class_id,flag_country,
             build_year,deadweight_tons,teu_capacity,
             gross_tonnage,status,owner_company)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            imo,
            "MV {} {}".format(fake.last_name(), random.choice(suffixes)),
            class_id, random.choice(flags),
            random.randint(1995,2023),
            dwt, teu,
            round(random.uniform(5000,80000),2),
            "Active", random.choice(owners)
        ))
        vessel_ids.append(last_id(cursor))
        if i % 50 == 0:
            conn.commit()
    conn.commit()
    print("  OK")

    # TERMINALS & BERTHS
    print("  3.6 Terminals et berths...")
    t_types = ["Container Terminal","Bulk Terminal",
               "Oil Terminal","RoRo Terminal","General Cargo"]
    berth_ids = []
    for pid in port_ids:
        for j in range(random.randint(2,4)):
            cursor.execute("""
                INSERT INTO terminals
                (port_id,terminal_name,terminal_type,berth_count,max_depth_m)
                VALUES (?,?,?,?,?)
            """, (pid, "Terminal {}".format(chr(65+j)),
                  random.choice(t_types),
                  random.randint(2,8),
                  round(random.uniform(10,18),1)))
            tid = last_id(cursor)
            for k in range(random.randint(2,4)):
                cursor.execute("""
                    INSERT INTO berths
                    (terminal_id,berth_name,length_m,depth_m,berth_type)
                    VALUES (?,?,?,?,?)
                """, (tid, "Berth {}".format(k+1),
                      round(random.uniform(150,400),1),
                      round(random.uniform(10,18),1),
                      random.choice(["General","Container","Bulk","Tanker"])))
                berth_ids.append(last_id(cursor))
    conn.commit()
    print("  OK")

    # CLIENTS
    print("  3.7 Clients...")
    segments = ["Tier 1 - Strategic","Tier 2 - Key Account","Tier 3 - Standard"]
    client_ids = []
    for i in range(80):
        cursor.execute("""
            INSERT INTO clients
            (client_code,company_name,country,segment,credit_limit,payment_terms)
            VALUES (?,?,?,?,?,?)
        """, ("CLT{:04d}".format(i+1), fake.company(), fake.country(),
              random.choice(segments),
              round(random.uniform(500000,5000000),2),
              random.choice([30,45,60,90])))
        client_ids.append(last_id(cursor))
    conn.commit()
    print("  OK")

    # SEAFARERS
    print("  3.8 500 seafarers...")
    ranks = ["Captain","Chief Officer","Second Officer",
             "Third Officer","Chief Engineer","Second Engineer",
             "Electrician","Bosun","AB Seaman"]
    nationalities = ["Filipino","Indian","Chinese","Ukrainian",
                     "Russian","Greek","Indonesian","Myanmar",
                     "Croatian","Polish"]
    seafarer_ids = []
    for i in tqdm(range(500)):
        cursor.execute("""
            INSERT INTO seafarers
            (seafarer_code,full_name,nationality,rank_title,
             date_of_birth,stcw_number)
            VALUES (?,?,?,?,?,?)
        """, ("SEA{:05d}".format(i+1), fake.name(),
              random.choice(nationalities),
              random.choice(ranks),
              fake.date_of_birth(minimum_age=22,maximum_age=60),
              "STCW{}".format(random.randint(100000,999999))))
        seafarer_ids.append(last_id(cursor))
        if i % 100 == 0:
            conn.commit()
    conn.commit()
    print("  OK")

    # VOYAGES
    print("  3.9 18,000 voyages...")
    start_date = datetime(2021,1,1)
    voyage_ids = []
    statuses = ["Completed","Completed","Completed","In Progress","Planned"]
    for i in tqdm(range(18000)):
        origin = random.choice(port_ids)
        dest   = random.choice([p for p in port_ids if p != origin])
        etd    = start_date + timedelta(days=random.randint(0,1095))
        eta    = etd + timedelta(days=random.uniform(5,45))
        status = "Planned" if eta > datetime.now() else random.choice(statuses)
        atd    = etd + timedelta(hours=random.uniform(-2,6)) if status != "Planned" else None
        ata    = eta + timedelta(hours=random.uniform(-12,24)) if status == "Completed" else None
        cursor.execute("""
            INSERT INTO voyages
            (voyage_code,vessel_id,origin_port_id,destination_port_id,
             etd,atd,eta,ata,distance_nm,voyage_status)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, ("VOY{:06d}".format(i+1), random.choice(vessel_ids),
              origin, dest, etd, atd, eta, ata,
              round(random.uniform(500,12000),2), status))
        voyage_ids.append(last_id(cursor))
        if i % 1000 == 0:
            conn.commit()
    conn.commit()
    print("  OK")

    # PORT CALLS
    print("  3.10 Port calls...")
    purposes = ["Loading","Discharging","Bunkering",
                "Crew Change","Repair","Inspection"]
    for i in tqdm(range(len(voyage_ids))):
        vid = voyage_ids[i]
        cursor.execute("SELECT etd,eta FROM voyages WHERE voyage_id=?", vid)
        v = cursor.fetchone()
        if not v or not v[0]:
            continue
        for _ in range(random.randint(1,2)):
            delta    = (v[1]-v[0]).days if v[1] else 10
            call_eta = v[0] + timedelta(days=random.uniform(1, max(1, delta*0.8)))
            call_etd = call_eta + timedelta(hours=random.uniform(12,72))
            cursor.execute("""
                INSERT INTO port_calls
                (voyage_id,port_id,berth_id,eta,ata,etd,atd,call_purpose)
                VALUES (?,?,?,?,?,?,?,?)
            """, (vid, random.choice(port_ids), random.choice(berth_ids),
                  call_eta,
                  call_eta + timedelta(hours=random.uniform(-2,4)),
                  call_etd,
                  call_etd + timedelta(hours=random.uniform(-1,3)),
                  random.choice(purposes)))
        if i % 2000 == 0:
            conn.commit()
    conn.commit()
    print("  OK")

    # CARGO ORDERS
    print("  3.11 25,000 cargo orders + manifests...")
    o_statuses = ["Confirmed","Loaded","Delivered","Cancelled"]
    for i in tqdm(range(25000)):
        vid = random.choice(voyage_ids)
        cursor.execute("""
            INSERT INTO cargo_orders
            (order_code,client_name,cargo_type_id,voyage_id,
             tonnage,volume_m3,freight_rate,order_status)
            VALUES (?,?,?,?,?,?,?,?)
        """, ("ORD{:07d}".format(i+1), fake.company(),
              random.choice(cargo_type_ids), vid,
              round(random.uniform(100,50000),2),
              round(random.uniform(50,30000),2),
              round(random.uniform(10,80),2),
              random.choice(o_statuses)))
        oid = last_id(cursor)
        cursor.execute("""
            INSERT INTO cargo_manifests
            (order_id,manifest_code,load_port_id,discharge_port_id,
             actual_tonnage,declared_value,customs_status)
            VALUES (?,?,?,?,?,?,?)
        """, (oid, "MAN{:07d}".format(i+1),
              random.choice(port_ids), random.choice(port_ids),
              round(random.uniform(100,50000),2),
              round(random.uniform(10000,5000000),2),
              random.choice(["Cleared","Pending","Inspected"])))
        if i % 1000 == 0:
            conn.commit()
    conn.commit()
    print("  OK")

    # CONTRACTS
    print("  3.12 Contracts...")
    c_types = ["Time Charter","Voyage Charter","COA","Bareboat"]
    for i in range(300):
        start = fake.date_between(start_date="-3y", end_date="today")
        end   = start + timedelta(days=random.randint(90,730))
        cursor.execute("""
            INSERT INTO contracts
            (contract_code,client_id,vessel_id,start_date,end_date,
             contract_type,base_rate,currency,contract_status)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, ("CTR{:05d}".format(i+1),
              random.choice(client_ids), random.choice(vessel_ids),
              start, end, random.choice(c_types),
              round(random.uniform(5000,35000),2),
              "USD",
              random.choice(["Active","Expired","Terminated"])))
    conn.commit()
    print("  OK")

    # BUNKERING
    print("  3.13 12,000 bunkering events...")
    suppliers = ["World Fuel Services","Peninsula","Bomin","Integr8","Bunker One"]
    for i in tqdm(range(12000)):
        cursor.execute("""
            INSERT INTO bunkering_events
            (vessel_id,port_id,fuel_grade_id,bunker_date,
             quantity_mt,unit_price_usd,total_cost_usd,supplier_name)
            VALUES (?,?,?,?,?,?,?,?)
        """, (random.choice(vessel_ids), random.choice(port_ids),
              random.choice(fuel_ids),
              fake.date_between(start_date="-3y", end_date="today"),
              round(random.uniform(50,3000),2),
              round(random.uniform(350,850),2),
              round(random.uniform(17500,2550000),2),
              random.choice(suppliers)))
        if i % 1000 == 0:
            conn.commit()
    conn.commit()
    print("  OK")

    # CREW ASSIGNMENTS
    print("  3.14 8,000 crew assignments...")
    for i in tqdm(range(8000)):
        vid = random.choice(voyage_ids)
        cursor.execute("SELECT etd,eta FROM voyages WHERE voyage_id=?", vid)
        v = cursor.fetchone()
        if not v or not v[0]:
            continue
        embark    = v[0].date()
        disembark = v[1].date() if v[1] else None
        cursor.execute("""
            INSERT INTO crew_assignments
            (seafarer_id,vessel_id,voyage_id,embark_date,
             disembark_date,role_onboard)
            VALUES (?,?,?,?,?,?)
        """, (random.choice(seafarer_ids), random.choice(vessel_ids), vid,
              embark, disembark, random.choice(ranks)))
        if i % 1000 == 0:
            conn.commit()
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("=" * 55)
    print("  Maritime Lakehouse Platform - Data Generator")
    print("  Target: YOUSSOUF\\SQLEXPRESS -> MaritimeDB")
    print("=" * 55)
    create_database()
    create_tables()
    populate_data()
    print("\n" + "=" * 55)
    print("  Generation terminee avec succes!")
    print("  - 150 vessels")
    print("  - 20 ports mondiaux")
    print("  - 18,000 voyages")
    print("  - ~36,000 port calls")
    print("  - 25,000 cargo orders + manifests")
    print("  - 300 contracts")
    print("  - 12,000 bunkering events")
    print("  - 8,000 crew assignments")
    print("  - 500 seafarers")
    print("=" * 55)
