from flask import Blueprint, render_template, jsonify, url_for
from functools import wraps
from flask import session, redirect, url_for

calendar_bp = Blueprint('calendar_bp', __name__)

def init_calendar_routes(app, get_db):

    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @calendar_bp.route('/admin/calendar')
    @admin_required
    def view_calendar():
        """Renders the main calendar view."""
        # Provide recent appointments payload (used by the weekly overview widget)
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute('''
                SELECT a.*, u.name as user_name
                FROM appointments a
                LEFT JOIN users u ON a.user_id = u.id
                WHERE a.status != 'cancelled'
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
                LIMIT 50
            ''')
            recent_appointments = [dict(row) for row in c.fetchall()]
        except Exception:
            recent_appointments = []
        finally:
            conn.close()

        dashboard_payload = {
            'recent_appointments': recent_appointments
        }

        return render_template('calendar/view.html', dashboard_payload=dashboard_payload)

    @calendar_bp.route('/api/appointments')
    @admin_required
    def api_appointments():
        """Provides appointment data as JSON for FullCalendar."""
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT id, patient_name, service, appointment_date, appointment_time, status
            FROM appointments
            WHERE status != 'cancelled'
        """)
        rows = c.fetchall()
        # ensure mapping access - convert sqlite rows to dicts if necessary
        try:
            appointments = [dict(r) for r in rows]
        except Exception:
            # fallback: assume rows are already dict-like
            appointments = rows
        conn.close()

        events = []
        for appt in appointments:
            # Build ISO start; if time is missing, use all-day event
            time = appt.get('appointment_time') or ''
            date = appt.get('appointment_date')
            if time and time.strip():
                # ensure time is HH:MM or HH:MM:SS
                start = f"{date}T{time}"
                all_day = False
            else:
                start = date
                all_day = True

            # color mapping per status
            status = (appt.get('status') or '').lower()
            color_map = {
                'pending': '#f39c12',
                'confirmed': '#2ecc71',
                'completed': '#3498db',
                'cancelled': '#e74c3c'
            }
            color = color_map.get(status, '#6c757d')

            events.append({
                'id': appt.get('id'),
                'title': f"{appt.get('patient_name') or 'Appointment'} - {appt.get('service') or ''}",
                'start': start,
                'allDay': all_day,
                'url': url_for('appointments.view_appointment', appointment_id=appt.get('id')) if appt.get('id') else None,
                'color': color,
                'extendedProps': {
                    'status': status,
                    'service': appt.get('service'),
                    'patient_name': appt.get('patient_name'),
                    'appointment_time': appt.get('appointment_time')
                }
            })
        
        return jsonify(events)

    app.register_blueprint(calendar_bp)
