from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATABASE_PATH = BASE_DIR / "comparethemotor.db"
DVLA_API_KEY = os.getenv("DVLA_API_KEY", "").strip()

SEED_VEHICLES = [
    {
        "id": "fiesta-2019",
        "make": "Ford",
        "model": "Fiesta Hatchback",
        "year": 2019,
        "engine": "1.0 EcoBoost",
        "price": 11995,
        "mpg": 54,
        "insurance_group": 10,
        "co2": 113,
        "horsepower": 99,
        "fuel_type": "Petrol",
        "image": "https://images.hgmsites.net/lrg/2019-ford-fiesta-st-hatch-angular-front-exterior-view_100674207_l.jpg",
        "mpg_note": None,
        "body_type": "Hatchback",
    },
    {
        "id": "corsa-2019",
        "make": "Vauxhall",
        "model": "Corsa Hatchback",
        "year": 2019,
        "engine": "1.2 Turbo",
        "price": 11450,
        "mpg": 52,
        "insurance_group": 10,
        "co2": 110,
        "horsepower": 100,
        "fuel_type": "Petrol",
        "image": "https://images.autouncle.com/uk/car_images/f2f12eee-df1e-463a-95c4-16b52bc1d6ee_2019-vauxhall-corsa-90.jpg",
        "mpg_note": None,
        "body_type": "Hatchback",
    },
    {
        "id": "golf-2020",
        "make": "Volkswagen",
        "model": "Golf",
        "year": 2020,
        "engine": "2.0 TDI",
        "price": 18500,
        "mpg": 60,
        "insurance_group": 16,
        "co2": 105,
        "horsepower": 150,
        "fuel_type": "Diesel",
        "image": "https://cdn.imagin.studio/getImage?customer=leasepoint&make=Volkswagen&modelFamily=Golf",
        "mpg_note": None,
        "body_type": "Hatchback",
    },
    {
        "id": "a250e-2020",
        "make": "Mercedes-Benz",
        "model": "A250e Saloon",
        "year": 2020,
        "engine": "1.3 Plug-in Hybrid",
        "price": 23000,
        "mpg": 201,
        "insurance_group": 25,
        "co2": 32,
        "horsepower": 215,
        "fuel_type": "Hybrid",
        "image": "https://api.vantage-leasing.com/storage/vehicles/ME028564/thumbs_a-class-saloon-meas-25.jpg",
        "mpg_note": "Official plug-in hybrid test-cycle figure. Real-world MPG may be lower depending on battery use and journey type.",
        "body_type": "Saloon",
    },
    {
        "id": "puma-2020",
        "make": "Ford",
        "model": "Puma",
        "year": 2020,
        "engine": "1.0 Hybrid",
        "price": 17500,
        "mpg": 50,
        "insurance_group": 12,
        "co2": 120,
        "horsepower": 125,
        "fuel_type": "Hybrid",
        "image": "https://www.goodwood.com/globalassets/.road--racing/road/news/2019/june/ford-puma/2019-ford-puma-goodwood-25062019.jpg",
        "mpg_note": None,
        "body_type": "SUV",
    },
    {
        "id": "bmw-330e",
        "make": "BMW",
        "model": "330e",
        "year": 2020,
        "engine": "2.0 Plug-in Hybrid",
        "price": 24000,
        "mpg": 140,
        "insurance_group": 30,
        "co2": 40,
        "horsepower": 288,
        "fuel_type": "Hybrid",
        "image": "https://mediapool.bmwgroup.com/cache/P9/201809/P90323742/P90323742-the-all-new-bmw-330e-sedan-10-2018-2002px.jpg",
        "mpg_note": "Official plug-in hybrid test-cycle figure. Real-world MPG may vary significantly depending on charging and trip length.",
        "body_type": "Saloon",
    },
]

DEMO_REGISTRATIONS = {
    "LC20FST": "fiesta-2019",
    "LD20CRS": "corsa-2019",
    "LE20GLF": "golf-2020",
    "LA20AAE": "a250e-2020",
    "LF20PMA": "puma-2020",
    "LB20BMW": "bmw-330e",
}

app = Flask(__name__, static_folder=str(PROJECT_DIR), static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database() -> None:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            id TEXT PRIMARY KEY,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER NOT NULL,
            engine TEXT NOT NULL,
            price INTEGER NOT NULL,
            mpg INTEGER NOT NULL,
            insurance_group INTEGER NOT NULL,
            co2 INTEGER NOT NULL,
            horsepower INTEGER NOT NULL,
            fuel_type TEXT NOT NULL,
            image TEXT NOT NULL,
            mpg_note TEXT,
            body_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS registration_matches (
            registration TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL,
            lookup_source TEXT NOT NULL DEFAULT 'demo',
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS lookup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration TEXT NOT NULL,
            source TEXT NOT NULL,
            exact_match INTEGER NOT NULL,
            matched_vehicle_id TEXT,
            returned_make TEXT,
            returned_model TEXT,
            returned_fuel_type TEXT,
            returned_year TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute("SELECT COUNT(*) AS total FROM vehicles")
    total = cursor.fetchone()["total"]

    if total == 0:
        cursor.executemany(
            """
            INSERT INTO vehicles (
                id, make, model, year, engine, price, mpg,
                insurance_group, co2, horsepower, fuel_type,
                image, mpg_note, body_type
            ) VALUES (
                :id, :make, :model, :year, :engine, :price, :mpg,
                :insurance_group, :co2, :horsepower, :fuel_type,
                :image, :mpg_note, :body_type
            )
            """,
            SEED_VEHICLES,
        )

    for registration, vehicle_id in DEMO_REGISTRATIONS.items():
        cursor.execute(
            """
            INSERT OR REPLACE INTO registration_matches (registration, vehicle_id, lookup_source)
            VALUES (?, ?, 'demo')
            """,
            (registration, vehicle_id),
        )

    connection.commit()
    connection.close()


def row_to_vehicle(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "id": row["id"],
        "make": row["make"],
        "model": row["model"],
        "year": row["year"],
        "engine": row["engine"],
        "price": row["price"],
        "mpg": row["mpg"],
        "insuranceGroup": row["insurance_group"],
        "co2": row["co2"],
        "horsepower": row["horsepower"],
        "fuelType": row["fuel_type"],
        "image": row["image"],
        "mpgNote": row["mpg_note"],
        "bodyType": row["body_type"],
    }


def clamp_score(value: float) -> float:
    return max(35.0, min(100.0, value))


def proportional_higher_better(current_value: float, other_value: float) -> float:
    ratio = (current_value / max(other_value, 1)) * 100
    return clamp_score(ratio)


def proportional_lower_better(current_value: float, other_value: float) -> float:
    ratio = (other_value / max(current_value, 1)) * 100
    return clamp_score(ratio)


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def get_weights(priority: str) -> dict[str, float]:
    profiles = {
        "balanced": {"affordability": 0.40, "efficiency": 0.35, "performance": 0.25},
        "affordability": {"affordability": 0.55, "efficiency": 0.25, "performance": 0.20},
        "efficiency": {"affordability": 0.25, "efficiency": 0.55, "performance": 0.20},
        "performance": {"affordability": 0.20, "efficiency": 0.20, "performance": 0.60},
    }
    return profiles.get(priority, profiles["balanced"])


def calculate_scores(current_car: dict[str, Any], other_car: dict[str, Any], priority: str) -> dict[str, int]:
    weights = get_weights(priority)

    affordability = average(
        [
            proportional_lower_better(current_car["price"], other_car["price"]),
            proportional_lower_better(current_car["insuranceGroup"], other_car["insuranceGroup"]),
        ]
    )

    efficiency = average(
        [
            proportional_higher_better(current_car["mpg"], other_car["mpg"]),
            proportional_lower_better(current_car["co2"], other_car["co2"]),
        ]
    )

    performance = proportional_higher_better(
        current_car["horsepower"], other_car["horsepower"]
    )

    overall = round(
        affordability * weights["affordability"]
        + efficiency * weights["efficiency"]
        + performance * weights["performance"]
    )

    return {
        "affordability": round(affordability),
        "efficiency": round(efficiency),
        "performance": round(performance),
        "overall": overall,
    }


def build_recommendation(
    vehicle_a: dict[str, Any],
    score_a: dict[str, int],
    vehicle_b: dict[str, Any],
    score_b: dict[str, int],
) -> str:
    if score_a["overall"] == score_b["overall"]:
        return (
            f"{vehicle_a['make']} {vehicle_a['model']} and {vehicle_b['make']} {vehicle_b['model']} "
            "are closely matched overall. The final choice depends on whether the buyer values "
            "affordability, efficiency, or performance more."
        )

    winner = vehicle_a if score_a["overall"] > score_b["overall"] else vehicle_b
    loser = vehicle_b if score_a["overall"] > score_b["overall"] else vehicle_a
    winner_score = score_a if score_a["overall"] > score_b["overall"] else score_b

    strengths: list[str] = []
    if winner_score["affordability"] >= 70:
        strengths.append("affordability")
    if winner_score["efficiency"] >= 70:
        strengths.append("efficiency")
    if winner_score["performance"] >= 70:
        strengths.append("performance")

    strength_text = " and ".join(strengths) if strengths else "overall balance"

    return (
        f"Recommendation: {winner['make']} {winner['model']} is the stronger overall choice, "
        f"particularly in {strength_text}. However, {loser['make']} {loser['model']} may still "
        "suit buyers with different priorities."
    )


def normalise_registration(registration: str) -> str:
    return "".join(registration.upper().split())


def get_vehicle_by_id(vehicle_id: str) -> dict[str, Any] | None:
    connection = get_db_connection()
    row = connection.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
    connection.close()
    return row_to_vehicle(row)


def log_lookup(
    registration: str,
    source: str,
    exact_match: bool,
    matched_vehicle_id: str | None,
    returned_make: str | None,
    returned_model: str | None,
    returned_fuel_type: str | None,
    returned_year: str | None,
) -> None:
    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO lookup_history (
            registration, source, exact_match, matched_vehicle_id,
            returned_make, returned_model, returned_fuel_type, returned_year
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            registration,
            source,
            1 if exact_match else 0,
            matched_vehicle_id,
            returned_make,
            returned_model,
            returned_fuel_type,
            returned_year,
        ),
    )
    connection.commit()
    connection.close()


def find_local_match_from_dvla(official_data: dict[str, Any]) -> dict[str, Any] | None:
    make = (official_data.get("make") or "").strip().lower()
    fuel_type = (official_data.get("fuelType") or "").strip().lower()
    year = official_data.get("yearOfManufacture")

    connection = get_db_connection()
    rows = connection.execute("SELECT * FROM vehicles").fetchall()
    connection.close()

    vehicles = [row_to_vehicle(row) for row in rows]

    exact_candidates = [
        vehicle
        for vehicle in vehicles
        if vehicle
        and vehicle["make"].lower() == make
        and vehicle["fuelType"].lower() == fuel_type
        and str(vehicle["year"]) == str(year)
    ]
    if exact_candidates:
        return exact_candidates[0]

    make_candidates = [vehicle for vehicle in vehicles if vehicle and vehicle["make"].lower() == make]
    if make_candidates:
        return make_candidates[0]

    return None


def get_suggestions_by_make(make: str | None) -> list[dict[str, Any]]:
    if not make:
        return []
    connection = get_db_connection()
    rows = connection.execute("SELECT * FROM vehicles WHERE LOWER(make) = LOWER(?)", (make,)).fetchall()
    connection.close()
    return [row_to_vehicle(row) for row in rows if row_to_vehicle(row)]


def build_demo_lookup(registration: str) -> dict[str, Any] | None:
    connection = get_db_connection()
    row = connection.execute(
        """
        SELECT v.* FROM registration_matches rm
        JOIN vehicles v ON v.id = rm.vehicle_id
        WHERE rm.registration = ?
        """,
        (registration,),
    ).fetchone()
    connection.close()

    vehicle = row_to_vehicle(row)
    if not vehicle:
        return None

    official_data = {
        "registrationNumber": registration,
        "make": vehicle["make"],
        "model": vehicle["model"],
        "fuelType": vehicle["fuelType"],
        "yearOfManufacture": vehicle["year"],
        "co2Emissions": vehicle["co2"],
        "engineDescription": vehicle["engine"],
        "source": "demo",
    }

    log_lookup(
        registration=registration,
        source="demo",
        exact_match=True,
        matched_vehicle_id=vehicle["id"],
        returned_make=official_data["make"],
        returned_model=official_data["model"],
        returned_fuel_type=official_data["fuelType"],
        returned_year=str(official_data["yearOfManufacture"]),
    )

    return {
        "success": True,
        "registration": registration,
        "source": "demo-local-database",
        "exactMatch": True,
        "vehicle": vehicle,
        "officialData": official_data,
    }


def call_dvla_api(registration: str) -> dict[str, Any]:
    url = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"
    response = requests.post(
        url,
        headers={
            "x-api-key": DVLA_API_KEY,
            "Content-Type": "application/json",
        },
        json={"registrationNumber": registration},
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


@app.route("/")
def serve_index() -> Any:
    return send_from_directory(PROJECT_DIR, "index.html")


@app.get("/api/health")
def api_health() -> Any:
    initialise_database()
    return jsonify(
        {
            "status": "ok",
            "database": DATABASE_PATH.name,
            "dvlaConfigured": bool(DVLA_API_KEY),
        }
    )


@app.get("/api/vehicles")
def api_get_vehicles() -> Any:
    max_budget = request.args.get("max_budget", default="999999")
    fuel_type = request.args.get("fuel_type", default="All")

    try:
        max_budget_int = int(max_budget)
    except ValueError:
        max_budget_int = 999999

    connection = get_db_connection()
    rows = connection.execute(
        """
        SELECT * FROM vehicles
        WHERE price <= ?
        AND (? = 'All' OR fuel_type = ?)
        ORDER BY price ASC, make ASC, model ASC
        """,
        (max_budget_int, fuel_type, fuel_type),
    ).fetchall()
    connection.close()

    vehicles = [row_to_vehicle(row) for row in rows if row_to_vehicle(row)]
    return jsonify(vehicles)


@app.post("/api/compare")
def api_compare() -> Any:
    payload = request.get_json(silent=True) or {}

    vehicle_a_id = payload.get("vehicle_a_id")
    vehicle_b_id = payload.get("vehicle_b_id")
    buyer_priority = payload.get("buyer_priority", "balanced")

    if not vehicle_a_id or not vehicle_b_id:
        return jsonify({"error": "Two vehicle IDs are required."}), 400

    if vehicle_a_id == vehicle_b_id:
        return jsonify({"error": "Please select two different vehicles."}), 400

    vehicle_a = get_vehicle_by_id(vehicle_a_id)
    vehicle_b = get_vehicle_by_id(vehicle_b_id)

    if not vehicle_a or not vehicle_b:
        return jsonify({"error": "One or both vehicles could not be found."}), 404

    score_a = calculate_scores(vehicle_a, vehicle_b, buyer_priority)
    score_b = calculate_scores(vehicle_b, vehicle_a, buyer_priority)

    winner_id = None
    if score_a["overall"] > score_b["overall"]:
        winner_id = vehicle_a["id"]
    elif score_b["overall"] > score_a["overall"]:
        winner_id = vehicle_b["id"]

    recommendation = build_recommendation(vehicle_a, score_a, vehicle_b, score_b)

    return jsonify(
        {
            "vehicleA": vehicle_a,
            "vehicleB": vehicle_b,
            "scoreA": score_a,
            "scoreB": score_b,
            "winnerId": winner_id,
            "buyerPriority": buyer_priority,
            "recommendation": recommendation,
        }
    )


@app.post("/api/lookup-registration")
def api_lookup_registration() -> Any:
    payload = request.get_json(silent=True) or {}
    registration = normalise_registration(payload.get("registration", ""))

    if not registration:
        return jsonify({"error": "A registration number is required."}), 400

    if len(registration) < 6:
        return jsonify({"error": "Registration format looks too short."}), 400

    demo_result = build_demo_lookup(registration)
    if demo_result:
        return jsonify(demo_result)

    if not DVLA_API_KEY:
        return jsonify(
            {
                "error": "Registration not found in the built-in demo list, and no DVLA API key is configured.",
            }
        ), 404

    try:
        official_data = call_dvla_api(registration)
    except requests.HTTPError as error:
        return jsonify({"error": f"DVLA lookup failed: {error.response.text}"}), 502
    except requests.RequestException as error:
        return jsonify({"error": f"DVLA request error: {str(error)}"}), 502

    matched_vehicle = find_local_match_from_dvla(official_data)
    suggestions = get_suggestions_by_make(official_data.get("make"))

    if matched_vehicle:
        log_lookup(
            registration=registration,
            source="dvla-live",
            exact_match=True,
            matched_vehicle_id=matched_vehicle["id"],
            returned_make=official_data.get("make"),
            returned_model=matched_vehicle["model"],
            returned_fuel_type=official_data.get("fuelType"),
            returned_year=str(official_data.get("yearOfManufacture")),
        )
        return jsonify(
            {
                "success": True,
                "registration": registration,
                "source": "dvla-live",
                "exactMatch": True,
                "vehicle": matched_vehicle,
                "officialData": official_data,
            }
        )

    log_lookup(
        registration=registration,
        source="dvla-live",
        exact_match=False,
        matched_vehicle_id=None,
        returned_make=official_data.get("make"),
        returned_model=None,
        returned_fuel_type=official_data.get("fuelType"),
        returned_year=str(official_data.get("yearOfManufacture")),
    )

    return jsonify(
        {
            "success": True,
            "registration": registration,
            "source": "dvla-live",
            "exactMatch": False,
            "vehicle": None,
            "officialData": official_data,
            "suggestions": suggestions,
        }
    )


if __name__ == "__main__":
    initialise_database()
    app.run(host="127.0.0.1", port=5000, debug=True)
