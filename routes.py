"""
EaseCargo API Routes
RESTful endpoints for shipments, bookings, recommendations, cities, and tracking.
"""

import json
import math
import os
import time
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from models import db, Shipment, Booking, User
from fuzzy_engine import (
    compute_match_score,
    calculate_capacity_fit,
    calculate_cost_efficiency,
    calculate_urgency,
)

api = Blueprint('api', __name__, url_prefix='/api')

# ──────────────────────── CITY COORDINATES ────────────────────────

_city_coords = None

# In-memory tracking simulation clock.
# Resets on Flask process restart, which is ideal for demo scenarios.
TRACKING_TICK_SECONDS = 0.5
TRACKING_PROGRESS_PER_TICK = 1.0
_tracking_clock = {}


def get_city_coords():
    """Load city coordinates from JSON file (cached)."""
    global _city_coords
    if _city_coords is None:
        path = os.path.join(os.path.dirname(__file__), 'data', 'city_coordinates.json')
        with open(path, 'r') as f:
            _city_coords = json.load(f)
    return _city_coords


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _advance_tracking_progress(shipment_pk):
    """Advance per-shipment simulated progress using a monotonic clock."""
    now = time.monotonic()
    state = _tracking_clock.get(shipment_pk)

    if state is None:
        state = {
            'progress': 0.0,
            'last_update': now,
        }
        _tracking_clock[shipment_pk] = state
        return state['progress'], False

    previous_progress = state['progress']
    elapsed = now - state['last_update']
    ticks = int(elapsed / TRACKING_TICK_SECONDS)

    if ticks > 0:
        state['progress'] = min(100.0, state['progress'] + ticks * TRACKING_PROGRESS_PER_TICK)
        state['last_update'] += ticks * TRACKING_TICK_SECONDS

    just_completed = previous_progress < 100.0 and state['progress'] >= 100.0
    return state['progress'], just_completed


def _mark_bookings_completed(shipment_pk):
    """Mark all active bookings on this shipment as completed."""
    updated = Booking.query.filter(
        Booking.shipment_id == shipment_pk,
        Booking.status != 'completed',
    ).update({'status': 'completed'}, synchronize_session=False)

    if updated:
        db.session.commit()


def estimate_transit_days(source_city, destination_city, transport_mode):
    """Estimate shipment transit time in days based on mode and route distance."""
    mode = (transport_mode or '').strip().lower()

    # Baseline durations if coordinates are unavailable
    baseline_days = {
        'air': 3,
        'sea': 16,
        'road': 5,
        'rail': 7,
    }

    coords = get_city_coords()
    source = coords.get(source_city)
    destination = coords.get(destination_city)

    if not source or not destination:
        days = baseline_days.get(mode, 7)
        return days, f"{days} days"

    distance_km = haversine(source['lat'], source['lon'], destination['lat'], destination['lon'])

    # Effective km/day includes handling, loading and transfer overhead.
    km_per_day = {
        'air': 2800,
        'sea': 420,
        'road': 750,
        'rail': 900,
    }
    fixed_overhead_days = {
        'air': 1.5,
        'sea': 4.0,
        'road': 1.0,
        'rail': 1.2,
    }

    speed = km_per_day.get(mode, 750)
    overhead = fixed_overhead_days.get(mode, 1.0)
    days = max(1, int(round(distance_km / speed + overhead)))

    return days, f"{days} day" if days == 1 else f"{days} days"


# ──────────────────────── CITIES ────────────────────────

@api.route('/cities', methods=['GET'])
def get_cities():
    """Get all unique cities from shipments + coordinates."""
    coords = get_city_coords()

    # Get cities actually in db
    sources = db.session.query(Shipment.source_city).distinct().all()
    destinations = db.session.query(Shipment.destination_city).distinct().all()
    db_cities = sorted(set([c[0] for c in sources] + [c[0] for c in destinations]))

    city_list = []
    for city in db_cities:
        entry = {'name': city}
        if city in coords:
            entry['lat'] = coords[city]['lat']
            entry['lon'] = coords[city]['lon']
            entry['country'] = coords[city].get('country', '')
        city_list.append(entry)

    return jsonify({'cities': city_list, 'count': len(city_list)})


@api.route('/cities/nearby', methods=['GET'])
def get_nearby_cities():
    """Find cities near a given city or coordinate."""
    city_name = request.args.get('city', '')
    radius_km = float(request.args.get('radius', 500))
    coords = get_city_coords()

    if city_name and city_name in coords:
        lat = coords[city_name]['lat']
        lon = coords[city_name]['lon']
    elif request.args.get('lat') and request.args.get('lon'):
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
    else:
        return jsonify({'error': 'Provide a city name or lat/lon'}), 400

    nearby = []
    for name, c in coords.items():
        if name == city_name:
            continue
        dist = haversine(lat, lon, c['lat'], c['lon'])
        if dist <= radius_km:
            nearby.append({
                'name': name,
                'lat': c['lat'],
                'lon': c['lon'],
                'country': c.get('country', ''),
                'distance_km': round(dist, 1),
            })

    nearby.sort(key=lambda x: x['distance_km'])
    return jsonify({'reference_city': city_name, 'radius_km': radius_km, 'nearby_cities': nearby})


@api.route('/city-coordinates', methods=['GET'])
def get_city_coordinates():
    """Return all city coordinates for map use."""
    return jsonify(get_city_coords())


# ──────────────────────── SHIPMENTS ────────────────────────

@api.route('/shipments', methods=['GET'])
def get_shipments():
    """
    Get shipments with filtering.
    Query params: source, destination, mode, min_capacity, max_cost, page, per_page
    """
    query = Shipment.query

    source = request.args.get('source', '').strip()
    destination = request.args.get('destination', '').strip()
    mode = request.args.get('mode', '').strip()
    min_capacity = request.args.get('min_capacity', type=float)
    max_cost = request.args.get('max_cost', type=float)
    status = request.args.get('status', 'available').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if source:
        query = query.filter(Shipment.source_city.ilike(f'%{source}%'))
    if destination:
        query = query.filter(Shipment.destination_city.ilike(f'%{destination}%'))
    if mode:
        query = query.filter(Shipment.transport_mode.ilike(mode))
    if min_capacity is not None:
        query = query.filter(Shipment.remaining_capacity_kg >= min_capacity)
    if max_cost is not None:
        query = query.filter(Shipment.cost_per_kg <= max_cost)
    if status:
        query = query.filter(Shipment.status == status)

    paginated = query.order_by(Shipment.shipment_date.asc()).paginate(
        page=page, per_page=min(per_page, 100), error_out=False
    )

    # Check if empty result and source/dest provided — suggest nearby
    suggestions = {}
    if paginated.total == 0 and (source or destination):
        coords = get_city_coords()
        if source and source not in coords:
            # Find closest city name match
            suggestions['source_alternatives'] = _find_nearby_alternatives(source, coords)
        if destination and destination not in coords:
            suggestions['destination_alternatives'] = _find_nearby_alternatives(destination, coords)

    shipments = []
    for s in paginated.items:
        payload = s.to_dict()
        eta_days, eta_text = estimate_transit_days(
            s.source_city,
            s.destination_city,
            s.transport_mode,
        )
        payload['estimated_transit_days'] = eta_days
        payload['estimated_transit_text'] = eta_text
        shipments.append(payload)

    result = {
        'shipments': shipments,
        'total': paginated.total,
        'page': paginated.page,
        'pages': paginated.pages,
        'per_page': per_page,
    }
    if suggestions:
        result['suggestions'] = suggestions

    return jsonify(result)


def _find_nearby_alternatives(city_name, coords):
    """Find alternative city name suggestions using string similarity."""
    alternatives = []
    city_lower = city_name.lower()
    for name in coords:
        if city_lower in name.lower() or name.lower() in city_lower:
            alternatives.append(name)
    # If no substring matches, return closest by name
    if not alternatives:
        alternatives = sorted(
            coords.keys(),
            key=lambda n: _simple_distance(city_lower, n.lower())
        )[:5]
    return alternatives[:5]


def _simple_distance(s1, s2):
    """Simple edit distance approximation."""
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1
    # Simple character overlap score
    common = sum(1 for c in s1 if c in s2)
    return max(len1, len2) - common


@api.route('/shipments/<int:shipment_id>', methods=['GET'])
def get_shipment(shipment_id):
    """Get a single shipment by ID."""
    shipment = Shipment.query.get_or_404(shipment_id)
    return jsonify(shipment.to_dict())


@api.route('/shipments/stats', methods=['GET'])
def get_shipment_stats():
    """Get aggregate statistics about shipments."""
    total = Shipment.query.count()
    available = Shipment.query.filter_by(status='available').count()

    modes = db.session.query(
        Shipment.transport_mode,
        db.func.count(Shipment.id),
        db.func.avg(Shipment.cost_per_kg),
        db.func.sum(Shipment.remaining_capacity_kg),
    ).group_by(Shipment.transport_mode).all()

    mode_stats = {}
    for mode, count, avg_cost, total_cap in modes:
        mode_stats[mode] = {
            'count': count,
            'avg_cost_per_kg': round(float(avg_cost), 2),
            'total_remaining_capacity_kg': round(float(total_cap), 1),
        }

    # Top routes
    top_routes = db.session.query(
        Shipment.source_city,
        Shipment.destination_city,
        db.func.count(Shipment.id).label('count'),
    ).group_by(
        Shipment.source_city, Shipment.destination_city
    ).order_by(db.text('count DESC')).limit(10).all()

    return jsonify({
        'total_shipments': total,
        'available_shipments': available,
        'by_transport_mode': mode_stats,
        'top_routes': [
            {'source': r[0], 'destination': r[1], 'count': r[2]}
            for r in top_routes
        ],
    })


@api.route('/transport-modes', methods=['GET'])
def get_transport_modes():
    """Get available transport modes."""
    modes = db.session.query(Shipment.transport_mode).distinct().all()
    return jsonify({'modes': sorted([m[0] for m in modes])})


# ──────────────────────── RECOMMENDATIONS ────────────────────────

@api.route('/recommend', methods=['POST'])
def recommend_shipments():
    """
    Get smart shipment recommendations using fuzzy logic.
    
    POST JSON body:
    {
        "source": "Mumbai",
        "destination": "London",
        "weight_kg": 500,
        "transport_mode": "Sea",      // optional
        "urgency": 50                   // optional, 0-100
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    source = data.get('source', '').strip()
    destination = data.get('destination', '').strip()
    weight_kg = data.get('weight_kg', 0)
    mode = data.get('transport_mode', '').strip()
    urgency_input = data.get('urgency', 50)

    if not source or not destination:
        return jsonify({'error': 'source and destination are required'}), 400
    if weight_kg <= 0:
        return jsonify({'error': 'weight_kg must be positive'}), 400

    # Build query
    query = Shipment.query.filter(
        Shipment.source_city.ilike(f'%{source}%'),
        Shipment.destination_city.ilike(f'%{destination}%'),
        Shipment.status == 'available',
        Shipment.remaining_capacity_kg >= weight_kg * 0.5,  # Allow partial fits
    )

    if mode:
        query = query.filter(Shipment.transport_mode.ilike(mode))

    candidates = query.limit(200).all()

    # If no exact matches, try nearby cities
    nearby_used = False
    if not candidates:
        coords = get_city_coords()
        nearby_sources = []
        nearby_dests = []

        if source in coords:
            for name, c in coords.items():
                if name != source:
                    dist = haversine(coords[source]['lat'], coords[source]['lon'], c['lat'], c['lon'])
                    if dist <= 500:
                        nearby_sources.append(name)

        if destination in coords:
            for name, c in coords.items():
                if name != destination:
                    dist = haversine(coords[destination]['lat'], coords[destination]['lon'], c['lat'], c['lon'])
                    if dist <= 500:
                        nearby_dests.append(name)

        if nearby_sources or nearby_dests:
            src_list = [source] + nearby_sources[:5]
            dst_list = [destination] + nearby_dests[:5]

            query = Shipment.query.filter(
                Shipment.source_city.in_(src_list),
                Shipment.destination_city.in_(dst_list),
                Shipment.status == 'available',
            )
            if mode:
                query = query.filter(Shipment.transport_mode.ilike(mode))
            candidates = query.limit(200).all()
            nearby_used = True

    if not candidates:
        return jsonify({
            'recommendations': [],
            'message': 'No matching shipments found. Try broadening your search.',
        })

    # Calculate fuzzy scores
    cost_values = [s.cost_per_kg for s in candidates]
    min_cost = min(cost_values)
    max_cost = max(cost_values)

    scored = []
    for ship in candidates:
        cap_fit = calculate_capacity_fit(ship.remaining_capacity_kg, weight_kg)
        cost_eff = calculate_cost_efficiency(ship.cost_per_kg, min_cost, max_cost)
        urgency_v = calculate_urgency(ship.shipment_date.isoformat(), urgency_input)

        result = compute_match_score(cap_fit, cost_eff, urgency_v)

        ship_dict = ship.to_dict()
        eta_days, eta_text = estimate_transit_days(
            ship.source_city,
            ship.destination_city,
            ship.transport_mode,
        )
        ship_dict['match'] = result
        ship_dict['estimated_cost'] = round(ship.cost_per_kg * weight_kg, 2)
        ship_dict['estimated_transit_days'] = eta_days
        ship_dict['estimated_transit_text'] = eta_text
        scored.append(ship_dict)

    # For high urgency, prioritize shorter transit times before score.
    if urgency_input >= 70:
        scored.sort(key=lambda x: (x.get('estimated_transit_days', 999), -x['match']['score']))
    else:
        scored.sort(key=lambda x: (-x['match']['score'], x.get('estimated_transit_days', 999)))

    return jsonify({
        'recommendations': scored[:20],
        'total_candidates': len(candidates),
        'nearby_city_search': nearby_used,
        'request': {
            'source': source,
            'destination': destination,
            'weight_kg': weight_kg,
            'transport_mode': mode or 'Any',
            'urgency': urgency_input,
        },
    })


# ──────────────────────── BOOKINGS ────────────────────────

@api.route('/bookings', methods=['POST'])
def create_booking():
    """
    Create a booking (reduces shipment capacity).
    
    POST JSON body:
    {
        "shipment_id": 1,
        "weight_kg": 200,
        "user_id": 1       // optional for demo
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    shipment_id = data.get('shipment_id')
    weight_kg = data.get('weight_kg', 0)
    user_id = data.get('user_id', 1)

    if not shipment_id or weight_kg <= 0:
        return jsonify({'error': 'shipment_id and positive weight_kg required'}), 400

    shipment = Shipment.query.get(shipment_id)
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404

    if shipment.remaining_capacity_kg < weight_kg:
        return jsonify({
            'error': f'Insufficient capacity. Available: {shipment.remaining_capacity_kg} kg',
        }), 400

    # Create booking
    booking_ref = f'BK-{uuid.uuid4().hex[:8].upper()}'
    total_cost = round(shipment.cost_per_kg * weight_kg, 2)

    booking = Booking(
        booking_ref=booking_ref,
        user_id=user_id,
        shipment_id=shipment.id,
        weight_kg=weight_kg,
        total_cost=total_cost,
    )

    # Reduce capacity
    shipment.remaining_capacity_kg = round(shipment.remaining_capacity_kg - weight_kg, 1)
    if shipment.remaining_capacity_kg <= 0:
        shipment.status = 'full'
    else:
        shipment.status = 'partially_booked'

    db.session.add(booking)
    db.session.commit()

    return jsonify({
        'message': 'Booking confirmed!',
        'booking': booking.to_dict(),
        'shipment_remaining_capacity': shipment.remaining_capacity_kg,
        'co2_saved_kg': round(weight_kg * 0.021, 2),  # Approx CO2 saved by space sharing
    }), 201


@api.route('/bookings', methods=['GET'])
def get_bookings():
    """Get all bookings, optionally filtered by user."""
    user_id = request.args.get('user_id', type=int)
    query = Booking.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    bookings = query.order_by(Booking.booked_at.desc()).all()

    payload = []
    for b in bookings:
        item = b.to_dict()
        if b.shipment:
            item['shipment_ref'] = b.shipment.shipment_id
        payload.append(item)

    return jsonify({'bookings': payload})


# ──────────────────────── TRACKING (SIMULATED) ────────────────────────

@api.route('/tracking/<int:shipment_id>', methods=['GET'])
def track_shipment(shipment_id):
    """
    Simulated shipment tracking.
    Returns source/destination coordinates and a simulated progress %.
    """
    shipment = Shipment.query.get_or_404(shipment_id)
    coords = get_city_coords()

    source_coords = coords.get(shipment.source_city, {})
    dest_coords = coords.get(shipment.destination_city, {})

    if not source_coords or not dest_coords:
        return jsonify({'error': 'Coordinates not available for this route'}), 404

    progress, just_completed = _advance_tracking_progress(shipment.id)

    if just_completed:
        _mark_bookings_completed(shipment.id)

    # Calculate current position (interpolated)
    current_lat = source_coords['lat'] + (dest_coords['lat'] - source_coords['lat']) * (progress / 100)
    current_lon = source_coords['lon'] + (dest_coords['lon'] - source_coords['lon']) * (progress / 100)

    distance = haversine(
        source_coords['lat'], source_coords['lon'],
        dest_coords['lat'], dest_coords['lon']
    )

    return jsonify({
        'shipment_id': shipment.shipment_id,
        'source': {
            'city': shipment.source_city,
            'lat': source_coords['lat'],
            'lon': source_coords['lon'],
        },
        'destination': {
            'city': shipment.destination_city,
            'lat': dest_coords['lat'],
            'lon': dest_coords['lon'],
        },
        'current_position': {
            'lat': round(current_lat, 4),
            'lon': round(current_lon, 4),
        },
        'progress_pct': round(progress, 1),
        'distance_km': round(distance, 1),
        'transport_mode': shipment.transport_mode,
        'status': 'In Transit' if progress < 100 else 'Completed',
        'just_completed': just_completed,
    })


# ──────────────────────── ENVIRONMENTAL IMPACT ────────────────────────

@api.route('/sustainability', methods=['GET'])
def get_sustainability_stats():
    """Get platform-wide sustainability metrics."""
    total_bookings = Booking.query.count()
    total_weight = db.session.query(db.func.sum(Booking.weight_kg)).scalar() or 0

    # Simulated sustainability metrics
    co2_saved = round(float(total_weight) * 0.021, 1)  # ~21g CO2 per kg shared
    trucks_avoided = int(float(total_weight) / 5000)  # Avg truck load
    trees_equivalent = round(co2_saved / 22, 1)  # ~22kg CO2 per tree per year

    return jsonify({
        'total_bookings': total_bookings,
        'total_weight_shared_kg': round(float(total_weight), 1),
        'co2_saved_kg': co2_saved,
        'trucks_avoided': trucks_avoided,
        'trees_equivalent': trees_equivalent,
    })


# ──────────────────────── USERS (BASIC) ────────────────────────

@api.route('/users', methods=['GET'])
def get_users():
    """Get all users."""
    users = User.query.all()
    return jsonify({'users': [u.to_dict() for u in users]})
