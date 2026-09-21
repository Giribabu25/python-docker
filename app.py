"""
Flight Booking System - Flask Web Application
Author: Developer
Description: A containerized REST API + Web UI for booking flights.
"""

import os
import random
import string
import datetime
from flask import Flask, jsonify, request, render_template, abort

# ------------------------------------------------------------------
# App Configuration
# ------------------------------------------------------------------
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ------------------------------------------------------------------
# In-Memory Data Store
# ------------------------------------------------------------------
FLIGHTS = []
BOOKINGS = {}

def _generate_booking_ref():
    """Generate a unique 6-character alphanumeric booking reference."""
    chars = string.ascii_uppercase + string.digits
    while True:
        ref = "".join(random.choices(chars, k=6))
        if ref not in BOOKINGS:
            return ref

def _seed_flights():
    """Populate the system with sample flight data."""
    base = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
    tomorrow = base + datetime.timedelta(days=1)
    next_week = base + datetime.timedelta(days=7)

    flights = [
        {
            "flight_number": "AA101",
            "origin": "New York (JFK)",
            "destination": "Los Angeles (LAX)",
            "departure": tomorrow.replace(hour=8, minute=0).isoformat(),
            "arrival": tomorrow.replace(hour=11, minute=30).isoformat(),
            "price": 320.00,
            "seats": 45,
        },
        {
            "flight_number": "UA202",
            "origin": "Chicago (ORD)",
            "destination": "Miami (MIA)",
            "departure": tomorrow.replace(hour=9, minute=15).isoformat(),
            "arrival": tomorrow.replace(hour=13, minute=0).isoformat(),
            "price": 280.50,
            "seats": 30,
        },
        {
            "flight_number": "DL303",
            "origin": "San Francisco (SFO)",
            "destination": "Seattle (SEA)",
            "departure": tomorrow.replace(hour=14, minute=0).isoformat(),
            "arrival": tomorrow.replace(hour=16, minute=15).isoformat(),
            "price": 150.00,
            "seats": 20,
        },
        {
            "flight_number": "SW404",
            "origin": "Dallas (DFW)",
            "destination": "Denver (DEN)",
            "departure": next_week.replace(hour=7, minute=30).isoformat(),
            "arrival": next_week.replace(hour=9, minute=0).isoformat(),
            "price": 190.75,
            "seats": 60,
        },
        {
            "flight_number": "BA505",
            "origin": "London (LHR)",
            "destination": "Paris (CDG)",
            "departure": next_week.replace(hour=10, minute=0).isoformat(),
            "arrival": next_week.replace(hour=12, minute=30).isoformat(),
            "price": 120.00,
            "seats": 15,
        },
        {
            "flight_number": "EK606",
            "origin": "Dubai (DXB)",
            "destination": "Mumbai (BOM)",
            "departure": next_week.replace(hour=20, minute=0).isoformat(),
            "arrival": next_week.replace(hour=23, minute=45).isoformat(),
            "price": 450.00,
            "seats": 25,
        },
    ]
    FLIGHTS.extend(flights)

# Seed data at import time
_seed_flights()

# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------
def _find_flight(flight_number):
    """Look up a flight by its flight number."""
    for flight in FLIGHTS:
        if flight["flight_number"].lower() == flight_number.lower():
            return flight
    return None

# ------------------------------------------------------------------
# Web UI Route
# ------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    """Render the main web interface."""
    return render_template("index.html")

# ------------------------------------------------------------------
# Health Check (used by Docker / orchestrators)
# ------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "flights": len(FLIGHTS),
        "bookings": len(BOOKINGS),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }), 200

# ------------------------------------------------------------------
# API: List / Search Flights
# ------------------------------------------------------------------
@app.route("/api/flights", methods=["GET"])
def list_flights():
    """
    GET /api/flights
    Optional query params:
      - origin: partial match (case-insensitive)
      - destination: partial match (case-insensitive)
    """
    origin = request.args.get("origin", "").strip().lower()
    destination = request.args.get("destination", "").strip().lower()

    results = FLIGHTS
    if origin:
        results = [f for f in results if origin in f["origin"].lower()]
    if destination:
        results = [f for f in results if destination in f["destination"].lower()]

    return jsonify({"count": len(results), "flights": results}), 200

# ------------------------------------------------------------------
# API: Get Single Flight
# ------------------------------------------------------------------
@app.route("/api/flights/<flight_number>", methods=["GET"])
def get_flight(flight_number):
    flight = _find_flight(flight_number)
    if not flight:
        return jsonify({"error": f"Flight {flight_number} not found"}), 404
    return jsonify(flight), 200

# ------------------------------------------------------------------
# API: Book a Flight
# ------------------------------------------------------------------
@app.route("/api/bookings", methods=["POST"])
def create_booking():
    """
    POST /api/bookings
    JSON body:
      {
        "flight_number": "AA101",
        "passenger_name": "John Doe",
        "passenger_email": "john@example.com"
      }
    """
    data = request.get_json(silent=True) or {}
    required = ["flight_number", "passenger_name", "passenger_email"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    flight = _find_flight(data["flight_number"])
    if not flight:
        return jsonify({"error": f"Flight {data['flight_number']} not found"}), 404

    if flight["seats"] <= 0:
        return jsonify({"error": "Flight is fully booked"}), 409

    # Reserve a seat
    flight["seats"] -= 1

    ref = _generate_booking_ref()
    booking = {
        "booking_ref": ref,
        "flight_number": flight["flight_number"],
        "origin": flight["origin"],
        "destination": flight["destination"],
        "departure": flight["departure"],
        "arrival": flight["arrival"],
        "price": flight["price"],
        "passenger_name": data["passenger_name"],
        "passenger_email": data["passenger_email"],
        "booked_at": datetime.datetime.utcnow().isoformat(),
    }
    BOOKINGS[ref] = booking

    return jsonify({
        "message": "Booking confirmed",
        "booking": booking,
    }), 201

# ------------------------------------------------------------------
# API: List All Bookings
# ------------------------------------------------------------------
@app.route("/api/bookings", methods=["GET"])
def list_bookings():
    return jsonify({
        "count": len(BOOKINGS),
        "bookings": list(BOOKINGS.values()),
    }), 200

# ------------------------------------------------------------------
# API: Get Booking by Reference
# ------------------------------------------------------------------
@app.route("/api/bookings/<booking_ref>", methods=["GET"])
def get_booking(booking_ref):
    booking = BOOKINGS.get(booking_ref.upper())
    if not booking:
        return jsonify({"error": f"Booking {booking_ref} not found"}), 404
    return jsonify(booking), 200

# ------------------------------------------------------------------
# API: Cancel Booking (restores seat)
# ------------------------------------------------------------------
@app.route("/api/bookings/<booking_ref>", methods=["DELETE"])
def cancel_booking(booking_ref):
    booking = BOOKINGS.pop(booking_ref.upper(), None)
    if not booking:
        return jsonify({"error": f"Booking {booking_ref} not found"}), 404

    # Restore seat to inventory
    flight = _find_flight(booking["flight_number"])
    if flight:
        flight["seats"] += 1

    return jsonify({"message": "Booking cancelled", "booking_ref": booking_ref}), 200

# ------------------------------------------------------------------
# Error Handlers
# ------------------------------------------------------------------
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Bind to 0.0.0.0 so the app is reachable from outside the container
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
