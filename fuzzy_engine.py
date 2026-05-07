"""
EaseCargo Fuzzy Logic Recommendation Engine
Uses scikit-fuzzy to compute match scores for shipments
based on capacity fit, cost efficiency, and urgency.
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


def build_fuzzy_system():
    """
    Build and return the fuzzy inference system.
    
    Inputs:
        - capacity_fit (0-100): How well the shipment capacity matches user needs.
              100 = perfect fit, 0 = very poor fit.
        - cost_efficiency (0-100): How cost-effective the shipment is.
              100 = cheapest option, 0 = most expensive.
        - urgency (0-100): How urgent the shipment timeline is.
              100 = extremely urgent, 0 = no urgency.
    
    Output:
        - match_score (0-100): Overall recommendation score.
    """

    # --- Antecedent (input) variables ---
    capacity_fit = ctrl.Antecedent(np.arange(0, 101, 1), 'capacity_fit')
    cost_efficiency = ctrl.Antecedent(np.arange(0, 101, 1), 'cost_efficiency')
    urgency = ctrl.Antecedent(np.arange(0, 101, 1), 'urgency')

    # --- Consequent (output) variable ---
    match_score = ctrl.Consequent(np.arange(0, 101, 1), 'match_score')

    # --- Membership functions for capacity_fit ---
    capacity_fit['poor'] = fuzz.trimf(capacity_fit.universe, [0, 0, 40])
    capacity_fit['average'] = fuzz.trimf(capacity_fit.universe, [20, 50, 80])
    capacity_fit['good'] = fuzz.trimf(capacity_fit.universe, [60, 100, 100])

    # --- Membership functions for cost_efficiency ---
    cost_efficiency['expensive'] = fuzz.trimf(cost_efficiency.universe, [0, 0, 40])
    cost_efficiency['moderate'] = fuzz.trimf(cost_efficiency.universe, [20, 50, 80])
    cost_efficiency['cheap'] = fuzz.trimf(cost_efficiency.universe, [60, 100, 100])

    # --- Membership functions for urgency ---
    urgency['low'] = fuzz.trimf(urgency.universe, [0, 0, 40])
    urgency['medium'] = fuzz.trimf(urgency.universe, [20, 50, 80])
    urgency['high'] = fuzz.trimf(urgency.universe, [60, 100, 100])

    # --- Membership functions for match_score ---
    match_score['poor'] = fuzz.trimf(match_score.universe, [0, 0, 30])
    match_score['below_average'] = fuzz.trimf(match_score.universe, [15, 30, 50])
    match_score['average'] = fuzz.trimf(match_score.universe, [35, 50, 65])
    match_score['good'] = fuzz.trimf(match_score.universe, [50, 70, 85])
    match_score['excellent'] = fuzz.trimf(match_score.universe, [70, 100, 100])

    # --- Fuzzy Rules (explainable, defensible) ---
    rules = [
        # High capacity fit drives high scores
        ctrl.Rule(capacity_fit['good'] & cost_efficiency['cheap'], match_score['excellent']),
        ctrl.Rule(capacity_fit['good'] & cost_efficiency['moderate'], match_score['good']),
        ctrl.Rule(capacity_fit['good'] & cost_efficiency['expensive'], match_score['average']),

        # Average capacity fit
        ctrl.Rule(capacity_fit['average'] & cost_efficiency['cheap'], match_score['good']),
        ctrl.Rule(capacity_fit['average'] & cost_efficiency['moderate'], match_score['average']),
        ctrl.Rule(capacity_fit['average'] & cost_efficiency['expensive'], match_score['below_average']),

        # Poor capacity fit
        ctrl.Rule(capacity_fit['poor'] & cost_efficiency['cheap'], match_score['average']),
        ctrl.Rule(capacity_fit['poor'] & cost_efficiency['moderate'], match_score['below_average']),
        ctrl.Rule(capacity_fit['poor'] & cost_efficiency['expensive'], match_score['poor']),

        # Urgency modifiers — high urgency boosts scores slightly
        ctrl.Rule(urgency['high'] & capacity_fit['good'], match_score['excellent']),
        ctrl.Rule(urgency['high'] & capacity_fit['average'], match_score['good']),
        ctrl.Rule(urgency['low'] & capacity_fit['poor'], match_score['poor']),
    ]

    system = ctrl.ControlSystem(rules)
    simulator = ctrl.ControlSystemSimulation(system)

    return simulator


# Pre-build the system once at module load
_fuzzy_sim = None


def get_fuzzy_simulator():
    """Get or create the fuzzy simulator singleton."""
    global _fuzzy_sim
    if _fuzzy_sim is None:
        _fuzzy_sim = build_fuzzy_system()
    return _fuzzy_sim


def compute_match_score(capacity_fit, cost_efficiency, urgency_val):
    """
    Compute matching score using fuzzy inference.
    
    Args:
        capacity_fit: 0-100 (how well capacity matches need)
        cost_efficiency: 0-100 (cost attractiveness)
        urgency_val: 0-100 (time urgency)
    
    Returns:
        dict with score and explanation
    """
    sim = get_fuzzy_simulator()

    # Clamp values to valid range
    capacity_fit = max(0.1, min(99.9, capacity_fit))
    cost_efficiency = max(0.1, min(99.9, cost_efficiency))
    urgency_val = max(0.1, min(99.9, urgency_val))

    sim.input['capacity_fit'] = capacity_fit
    sim.input['cost_efficiency'] = cost_efficiency
    sim.input['urgency'] = urgency_val

    try:
        sim.compute()
        score = round(sim.output['match_score'], 1)
    except Exception:
        # Fallback: weighted average if fuzzy engine fails
        score = round(0.45 * capacity_fit + 0.35 * cost_efficiency + 0.20 * urgency_val, 1)

    # Build human-readable explanation
    explanations = []
    if capacity_fit >= 70:
        explanations.append("Excellent capacity fit for your cargo size")
    elif capacity_fit >= 40:
        explanations.append("Reasonable capacity match")
    else:
        explanations.append("Capacity is a loose fit — consider splitting cargo")

    if cost_efficiency >= 70:
        explanations.append("Very cost-effective option")
    elif cost_efficiency >= 40:
        explanations.append("Moderately priced")
    else:
        explanations.append("Premium pricing tier")

    if urgency_val >= 70:
        explanations.append("Meets urgent timeline requirements")
    elif urgency_val >= 40:
        explanations.append("Flexible scheduling")
    else:
        explanations.append("Non-urgent — more options available")

    label = 'Poor'
    if score >= 80:
        label = 'Excellent'
    elif score >= 65:
        label = 'Good'
    elif score >= 45:
        label = 'Average'
    elif score >= 25:
        label = 'Below Average'

    return {
        'score': score,
        'label': label,
        'explanation': explanations,
        'inputs': {
            'capacity_fit': round(capacity_fit, 1),
            'cost_efficiency': round(cost_efficiency, 1),
            'urgency': round(urgency_val, 1),
        }
    }


def calculate_capacity_fit(remaining_kg, needed_kg):
    """Calculate how well the remaining capacity fits the needed weight."""
    if remaining_kg <= 0 or needed_kg <= 0:
        return 0
    if needed_kg > remaining_kg:
        return max(0, (1 - (needed_kg - remaining_kg) / needed_kg) * 60)
    ratio = needed_kg / remaining_kg
    if ratio >= 0.7:
        return 80 + (ratio - 0.7) / 0.3 * 20
    elif ratio >= 0.3:
        return 40 + (ratio - 0.3) / 0.4 * 40
    else:
        return ratio / 0.3 * 40


def calculate_cost_efficiency(cost_per_kg, min_cost, max_cost):
    """Calculate cost efficiency score (0-100, higher is cheaper)."""
    if max_cost <= min_cost:
        return 50
    return round((1 - (cost_per_kg - min_cost) / (max_cost - min_cost)) * 100, 1)


def calculate_urgency(shipment_date_str, days_until_needed=30):
    """Calculate urgency score based on how soon the shipment departs."""
    from datetime import datetime
    try:
        ship_date = datetime.strptime(shipment_date_str, '%Y-%m-%d')
        today = datetime.now()
        days_until_ship = (ship_date - today).days

        if days_until_ship <= 0:
            return 10  # Already passed
        if days_until_ship <= 3:
            return 95
        if days_until_ship <= 7:
            return 80
        if days_until_ship <= 14:
            return 60
        if days_until_ship <= 30:
            return 40
        return 20
    except Exception:
        return 50
