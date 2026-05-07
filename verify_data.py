#!/usr/bin/env python
"""Quick verification of loaded database data."""

from app import create_app
from models import Shipment

app = create_app()
with app.app_context():
    # Check Paris <-> Miami
    pm_routes = Shipment.query.filter(
        ((Shipment.source_city == 'Paris') & (Shipment.destination_city == 'Miami')) |
        ((Shipment.source_city == 'Miami') & (Shipment.destination_city == 'Paris'))
    ).all()
    
    print(f'Paris ↔ Miami routes in DB: {len(pm_routes)}')
    modes = {}
    for r in pm_routes:
        mode = r.transport_mode
        modes[mode] = modes.get(mode, 0) + 1
    
    for mode in sorted(modes.keys()):
        print(f'  {mode}: {modes[mode]}')
    
    if len(pm_routes) > 0:
        has_rail = any(r.transport_mode == 'Rail' for r in pm_routes)
        rail_status = "❌ YES - PROBLEM!" if has_rail else "✅ NO - Good!"
        print(f'Has Rail?: {rail_status}')
