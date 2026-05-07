"""
EaseCargo — Main Flask Application
Entry point for the Smart Container Space Matching Platform.
"""

import csv
import json
import os
from datetime import datetime

from flask import Flask, redirect, send_from_directory
from flask_cors import CORS

from config import config_map
from models import db, Shipment, User
from routes import api


def create_app(config_name='default'):
    """Application factory."""
    app = Flask(
        __name__,
        static_folder='static',
        static_url_path='/static',
    )
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # Initialize extensions
    CORS(app)
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(api)

    # Ensure instance directory exists
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    # Serve frontend pages
    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')

    @app.route('/smart-discover')
    def smart_discover():
        return send_from_directory('static', 'smart-discover.html')

    @app.route('/discover')
    def discover():
        return redirect('/smart-discover')

    @app.route('/recommend')
    def recommend():
        return redirect('/smart-discover?mode=fuzzy')

    @app.route('/tracking')
    def tracking():
        return send_from_directory('static', 'tracking.html')

    @app.route('/dashboard')
    def dashboard():
        return send_from_directory('static', 'dashboard.html')

    @app.route('/about')
    def about():
        return send_from_directory('static', 'about.html')

    # Initialize database on first request
    with app.app_context():
        db.create_all()
        _seed_data_if_empty(app)

    return app


def _seed_data_if_empty(app):
    """Load CSV data into the database if empty."""
    if Shipment.query.first() is not None:
        return

    csv_path = app.config['CSV_DATA_PATH']
    if not os.path.exists(csv_path):
        print(f"⚠ CSV not found at {csv_path}. Run data/generate_shipments.py first.")
        return

    print(f"🔄 Seeding database from {csv_path}...")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            shipment = Shipment(
                shipment_id=row['shipment_id'],
                source_city=row['source_city'],
                destination_city=row['destination_city'],
                transport_mode=row['transport_mode'],
                original_capacity_kg=float(row['original_capacity_kg']),
                remaining_capacity_kg=float(row['remaining_capacity_kg']),
                cost_per_kg=float(row['cost_per_kg']),
                shipment_date=datetime.strptime(row['shipment_date'], '%Y-%m-%d').date(),
                carrier_name=row.get('carrier_name', ''),
                status=row.get('status', 'available'),
            )
            batch.append(shipment)

            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []

        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()

    print(f"✅ Seeded {Shipment.query.count()} shipments")

    # Create demo users
    demo_users = [
        User(username='exporter_demo', email='exporter@demo.com', role='exporter', company_name='SmallTrade Co.'),
        User(username='logistics_demo', email='logistics@demo.com', role='logistics', company_name='GlobalFreight Co.'),
        User(username='admin_demo', email='admin@demo.com', role='admin', company_name='EaseCargo'),
    ]
    db.session.bulk_save_objects(demo_users)
    db.session.commit()
    print("✅ Created demo users")


# WSGI entrypoint for Gunicorn/Uvicorn-style servers.
# In containers, FLASK_ENV is set to production via docker-compose.
app = create_app(os.environ.get('FLASK_ENV', 'default'))

if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=True)
