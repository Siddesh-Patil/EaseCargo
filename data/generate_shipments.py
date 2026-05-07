"""
EaseCargo Synthetic Shipment Data Generator
Generates ~10,000 realistic shipment records as CSV.
"""

import csv
import json
import random
import os
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load city list
with open(os.path.join(SCRIPT_DIR, 'city_coordinates.json'), 'r') as f:
    CITIES = json.load(f)

CITY_NAMES = list(CITIES.keys())

TRANSPORT_MODES = ['Air', 'Sea', 'Road', 'Rail']

DOMESTIC_MODES = ['Air', 'Sea', 'Road', 'Rail']
INTERNATIONAL_MODES = ['Air', 'Sea']

CARRIER_NAMES = [
    'GlobalFreight Co.', 'OceanLink Logistics', 'SkyBridge Cargo',
    'RailConnect Express', 'TransWorld Shipping', 'EcoRoute Logistics',
    'SwiftCargo International', 'PrimeShip Solutions', 'AnchorLine Freight',
    'VelocityTrans', 'BridgePort Carriers', 'Pacific Trade Lines',
    'Nordic Freight Systems', 'Atlas Cargo Group', 'Meridian Logistics',
]

# Cost ranges per transport mode (USD per kg)
COST_RANGES = {
    'Air': (2.5, 12.0),
    'Sea': (0.3, 2.5),
    'Road': (0.8, 4.0),
    'Rail': (0.5, 3.0),
}

# Capacity ranges per transport mode (kg)
CAPACITY_RANGES = {
    'Air': (500, 15000),
    'Sea': (5000, 100000),
    'Road': (1000, 25000),
    'Rail': (2000, 50000),
}

# Transport mode weights - prioritize Air/Sea, minimal Road/Rail for domestic only
DOMESTIC_MODE_WEIGHTS = [0.45, 0.45, 0.07, 0.03]  # Air, Sea, Road, Rail
INTERNATIONAL_MODE_WEIGHTS = [0.25, 0.75]  # Air, Sea only (no Road/Rail for cross-border)


def choose_transport_mode(source_city, destination_city):
    """Choose a realistic transport mode based on route type.
    
    - Domestic (same country): All modes allowed, but Air/Sea strongly preferred
    - International (cross-country/continent): Air/Sea only
    """
    source_country = CITIES[source_city]['country']
    destination_country = CITIES[destination_city]['country']

    if source_country == destination_country:
        return random.choices(DOMESTIC_MODES, weights=DOMESTIC_MODE_WEIGHTS, k=1)[0]

    return random.choices(
        INTERNATIONAL_MODES,
        weights=INTERNATIONAL_MODE_WEIGHTS,
        k=1,
    )[0]


def generate_shipments(count=10000, output_path=None):
    """Generate synthetic shipment data."""
    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, 'shipments.csv')

    random.seed(42)
    base_date = datetime(2025, 1, 1)

    rows = []
    for i in range(1, count + 1):
        source = random.choice(CITY_NAMES)
        dest = random.choice([c for c in CITY_NAMES if c != source])
        mode = choose_transport_mode(source, dest)

        cap_min, cap_max = CAPACITY_RANGES[mode]
        original_capacity = round(random.uniform(cap_min, cap_max), 1)
        utilization = random.uniform(0.10, 0.85)  # 10-85% already used
        remaining = round(original_capacity * (1 - utilization), 1)

        cost_min, cost_max = COST_RANGES[mode]
        cost_per_kg = round(random.uniform(cost_min, cost_max), 2)

        ship_date = base_date + timedelta(days=random.randint(0, 365))
        carrier = random.choice(CARRIER_NAMES)

        rows.append({
            'shipment_id': f'EC-{i:06d}',
            'source_city': source,
            'destination_city': dest,
            'transport_mode': mode,
            'original_capacity_kg': original_capacity,
            'remaining_capacity_kg': remaining,
            'cost_per_kg': cost_per_kg,
            'shipment_date': ship_date.strftime('%Y-%m-%d'),
            'carrier_name': carrier,
            'status': 'available',
        })

    fieldnames = [
        'shipment_id', 'source_city', 'destination_city', 'transport_mode',
        'original_capacity_kg', 'remaining_capacity_kg', 'cost_per_kg',
        'shipment_date', 'carrier_name', 'status',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Generated {len(rows)} shipments → {output_path}")
    return output_path


if __name__ == '__main__':
    generate_shipments()
