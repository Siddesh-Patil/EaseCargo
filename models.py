"""
EaseCargo Database Models
SQLAlchemy models for Users, Shipments, and Bookings.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """User model supporting Exporter, Logistics Provider, and Admin roles."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='exporter')  # exporter, logistics, admin
    company_name = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    bookings = db.relationship('Booking', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'company_name': self.company_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Shipment(db.Model):
    """Shipment model representing a cargo shipment with available capacity."""
    __tablename__ = 'shipments'

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.String(20), unique=True, nullable=False)
    source_city = db.Column(db.String(100), nullable=False, index=True)
    destination_city = db.Column(db.String(100), nullable=False, index=True)
    transport_mode = db.Column(db.String(20), nullable=False)  # Air, Sea, Road, Rail
    remaining_capacity_kg = db.Column(db.Float, nullable=False)
    original_capacity_kg = db.Column(db.Float, nullable=False)
    cost_per_kg = db.Column(db.Float, nullable=False)
    shipment_date = db.Column(db.Date, nullable=False)
    carrier_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='available')  # available, partially_booked, full
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    bookings = db.relationship('Booking', backref='shipment', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'source_city': self.source_city,
            'destination_city': self.destination_city,
            'transport_mode': self.transport_mode,
            'remaining_capacity_kg': self.remaining_capacity_kg,
            'original_capacity_kg': self.original_capacity_kg,
            'cost_per_kg': self.cost_per_kg,
            'shipment_date': self.shipment_date.isoformat() if self.shipment_date else None,
            'carrier_name': self.carrier_name,
            'status': self.status,
            'utilization_pct': round(
                (1 - self.remaining_capacity_kg / self.original_capacity_kg) * 100, 1
            ) if self.original_capacity_kg > 0 else 0,
        }


class Booking(db.Model):
    """Booking model representing a capacity reservation by an exporter."""
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_ref = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, completed, cancelled
    booked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'booking_ref': self.booking_ref,
            'user_id': self.user_id,
            'shipment_id': self.shipment_id,
            'weight_kg': self.weight_kg,
            'total_cost': round(self.total_cost, 2),
            'status': self.status,
            'booked_at': self.booked_at.isoformat() if self.booked_at else None,
        }
