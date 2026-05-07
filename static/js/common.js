/**
 * EaseCargo — Common JavaScript Utilities
 * Shared across all pages.
 */

const API_BASE = '/api';

// ── Navbar Scroll Effect ──
window.addEventListener('scroll', () => {
    const navbar = document.getElementById('navbar');
    if (navbar) {
        navbar.classList.toggle('scrolled', window.scrollY > 30);
    }
});

// ── Mobile Menu Toggle ──
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('active');
        });
    }

    // ── Page Transition Overlay ──
    createPageTransition();

    // ── Button Ripple Effects ──
    initButtonRipples();

    // ── Page Enter Animation ──
    document.body.classList.add('page-enter');
});

// ══ PAGE TRANSITION SYSTEM ══
function createPageTransition() {
    // Create the overlay with gradient slices
    const overlay = document.createElement('div');
    overlay.className = 'page-transition-overlay';
    overlay.id = 'pageTransition';
    for (let i = 0; i < 5; i++) {
        const slice = document.createElement('div');
        slice.className = 'pt-slice';
        overlay.appendChild(slice);
    }
    document.body.appendChild(overlay);

    // Intercept navigation link clicks
    document.querySelectorAll('a[href]').forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            // Only intercept internal links (not #anchors, not external, not javascript:)
            if (!href || href.startsWith('#') || href.startsWith('javascript') ||
                href.startsWith('http') || link.target === '_blank') return;

            // Don't transition to current page
            if (href === window.location.pathname) return;

            e.preventDefault();
            const overlay = document.getElementById('pageTransition');
            overlay.classList.add('active');

            // Navigate after animation completes
            setTimeout(() => {
                window.location.href = href;
            }, 450);
        });
    });
}

// ══ BUTTON RIPPLE EFFECT ══
function initButtonRipples() {
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn');
        if (!btn) return;

        // Remove old ripples
        btn.querySelectorAll('.ripple').forEach(r => r.remove());

        const rect = btn.getBoundingClientRect();
        const ripple = document.createElement('span');
        ripple.className = 'ripple';

        const size = Math.max(rect.width, rect.height) * 2;
        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
        ripple.style.top = `${e.clientY - rect.top - size / 2}px`;

        btn.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
    });
}

// ── Toast Notifications ──
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ── API Helper ──
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        return data;
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// ── Debounce Utility ──
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ── Format Currency ──
function formatCost(amount) {
    return `$${parseFloat(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ── Transport Mode Icon ──
function getModeIcon(mode) {
    const icons = { Air: '✈️', Sea: '🚢', Road: '🚛', Rail: '🚂' };
    return icons[mode] || '📦';
}

// ── Transport Mode CSS Class ──
function getModeClass(mode) {
    return `mode-${(mode || '').toLowerCase()}`;
}

// ── Match Score CSS Class ──
function getMatchClass(label) {
    const map = {
        'Excellent': 'match-excellent',
        'Good': 'match-good',
        'Average': 'match-average',
        'Below Average': 'match-below-average',
        'Poor': 'match-poor',
    };
    return map[label] || 'match-average';
}

// ── City Autocomplete ──
let _cityCache = null;

async function loadCities() {
    if (_cityCache) return _cityCache;
    try {
        const data = await apiRequest('/cities');
        _cityCache = data.cities || [];
        return _cityCache;
    } catch {
        return [];
    }
}

function setupAutocomplete(inputId, listId) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);
    if (!input || !list) return;

    const filterCities = debounce(async () => {
        const query = input.value.trim().toLowerCase();
        if (query.length < 1) {
            list.classList.remove('active');
            return;
        }

        const cities = await loadCities();
        const matches = cities.filter(c =>
            c.name.toLowerCase().includes(query)
        ).slice(0, 10);

        if (matches.length === 0) {
            list.classList.remove('active');
            return;
        }

        list.innerHTML = matches.map(c => `
            <div class="autocomplete-item" data-city="${c.name}">
                <span>${c.name}</span>
                <span class="city-country">${c.country || ''}</span>
            </div>
        `).join('');

        list.classList.add('active');

        list.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                input.value = item.dataset.city;
                list.classList.remove('active');
                input.dispatchEvent(new Event('change'));
            });
        });
    }, 200);

    input.addEventListener('input', filterCities);
    input.addEventListener('focus', filterCities);

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.autocomplete-wrapper')) {
            list.classList.remove('active');
        }
    });
}

// ── Shipment Card HTML Generator ──
function createShipmentCard(shipment, showMatch = false, showBookBtn = true) {
    const modeClass = getModeClass(shipment.transport_mode);
    const modeIcon = getModeIcon(shipment.transport_mode);
    const utilization = shipment.utilization_pct || 0;
    const transitText = shipment.estimated_transit_text ||
        (shipment.estimated_transit_days ? `${shipment.estimated_transit_days} days` : null);

    let matchHtml = '';
    if (showMatch && shipment.match) {
        const matchClass = getMatchClass(shipment.match.label);
        matchHtml = `
            <div class="match-score ${matchClass}">
                ⚡ ${shipment.match.score} — ${shipment.match.label}
            </div>
            <div style="margin-top: 8px;">
                ${shipment.match.explanation.map(e => `<div style="font-size: 0.8rem; color: var(--text-muted);">• ${e}</div>`).join('')}
            </div>
        `;
    }

    return `
        <div class="shipment-card" data-id="${shipment.id}">
            <div class="shipment-route">
                <span class="shipment-city">${shipment.source_city}</span>
                <span class="shipment-arrow">→</span>
                <span class="shipment-city">${shipment.destination_city}</span>
            </div>
            <div class="shipment-meta">
                <span class="mode-badge ${modeClass}">${modeIcon} ${shipment.transport_mode}</span>
                <span class="shipment-meta-item">
                    <span class="meta-icon">📦</span>
                    ${shipment.remaining_capacity_kg.toLocaleString()} kg available
                </span>
                <span class="shipment-meta-item">
                    <span class="meta-icon">📅</span>
                    ${shipment.shipment_date}
                </span>
                ${transitText ? `
                <span class="shipment-meta-item">
                    <span class="meta-icon">⏱️</span>
                    ETA ${transitText}
                </span>` : ''}
            </div>
            ${matchHtml}
            <div style="margin-top: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px;">
                    <span>Container Utilization</span>
                    <span>${utilization}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${utilization}%"></div>
                </div>
            </div>
            <div class="shipment-actions">
                <div class="shipment-cost">
                    $${shipment.cost_per_kg} <span class="cost-unit">/ kg</span>
                    ${shipment.estimated_cost ? `<div style="font-size: 0.8rem; color: var(--text-muted);">Est. total: ${formatCost(shipment.estimated_cost)}</div>` : ''}
                </div>
                <div style="display: flex; gap: 8px;">
                    ${showBookBtn ? `<button class="btn btn-primary btn-sm" onclick="openBookingModal(${shipment.id}, '${shipment.source_city} → ${shipment.destination_city}', ${shipment.remaining_capacity_kg}, ${shipment.cost_per_kg})">Book Now</button>` : ''}
                    <a href="/tracking?id=${shipment.id}" class="btn btn-secondary btn-sm">Track</a>
                </div>
            </div>
        </div>
    `;
}

// ── Booking Modal ──
function openBookingModal(shipmentId, route, maxCapacity, costPerKg) {
    // Remove existing modal
    const existingModal = document.getElementById('bookingModal');
    if (existingModal) existingModal.remove();

    const modal = document.createElement('div');
    modal.id = 'bookingModal';
    modal.className = 'modal-overlay active';
    modal.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h2>📦 Book Cargo Space</h2>
                <button class="modal-close" onclick="closeBookingModal()">✕</button>
            </div>
            <div>
                <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                    Route: <strong style="color: var(--text-primary)">${route}</strong>
                </p>
                <div class="form-group">
                    <label class="form-label">Weight (kg)</label>
                    <input type="number" class="form-input" id="bookingWeight" 
                           min="1" max="${maxCapacity}" placeholder="Enter weight in kg"
                           oninput="updateBookingCost(${costPerKg})">
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">
                        Max available: ${maxCapacity.toLocaleString()} kg
                    </div>
                </div>
                <div style="background: var(--bg-glass); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="color: var(--text-secondary);">Cost per kg:</span>
                        <span>$${costPerKg}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 1.2rem; font-weight: 700;">
                        <span>Total Cost:</span>
                        <span class="text-accent" id="bookingTotalCost">$0.00</span>
                    </div>
                </div>
                <div id="bookingCo2" style="font-size: 0.85rem; color: var(--accent-400); text-align: center; margin-bottom: 1rem;">
                    🌱 Estimated CO₂ saved: 0 kg
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-ghost" onclick="closeBookingModal()">Cancel</button>
                <button class="btn btn-primary" id="confirmBookingBtn" onclick="confirmBooking(${shipmentId})">
                    Confirm Booking
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeBookingModal();
    });
}

function updateBookingCost(costPerKg) {
    const weight = parseFloat(document.getElementById('bookingWeight').value) || 0;
    const total = weight * costPerKg;
    document.getElementById('bookingTotalCost').textContent = formatCost(total);
    document.getElementById('bookingCo2').textContent = `🌱 Estimated CO₂ saved: ${(weight * 0.021).toFixed(1)} kg`;
}

function closeBookingModal() {
    const modal = document.getElementById('bookingModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

async function confirmBooking(shipmentId) {
    const weight = parseFloat(document.getElementById('bookingWeight').value);
    if (!weight || weight <= 0) {
        showToast('Please enter a valid weight', 'warning');
        return;
    }

    const btn = document.getElementById('confirmBookingBtn');
    btn.disabled = true;
    btn.textContent = 'Processing...';

    try {
        const result = await apiRequest('/bookings', {
            method: 'POST',
            body: JSON.stringify({ shipment_id: shipmentId, weight_kg: weight }),
        });

        closeBookingModal();
        showToast(`Booking confirmed! Ref: ${result.booking.booking_ref} | Total: ${formatCost(result.booking.total_cost)}`, 'success', 6000);

        // Refresh page data if applicable
        if (typeof refreshResults === 'function') refreshResults();
    } catch (err) {
        showToast(err.message || 'Booking failed', 'error');
        btn.disabled = false;
        btn.textContent = 'Confirm Booking';
    }
}
