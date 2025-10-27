from flask import Blueprint, render_template, jsonify
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
        return render_template('calendar/view.html')

    @calendar_bp.route('/api/appointments')
    @admin_required
    def api_appointments():
        """Provides appointment data as JSON for FullCalendar."""
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT patient_name, service, appointment_date, appointment_time
            FROM appointments
            WHERE status != 'cancelled'
        """)
        appointments = c.fetchall()
        conn.close()

        events = []
        for appt in appointments:
            start_datetime = f"{appt['appointment_date']}T{appt['appointment_time']}"
            events.append({
                'title': f"{appt['patient_name']} - {appt['service']}",
                'start': start_datetime
            })
        
        return jsonify(events)

    app.register_blueprint(calendar_bp)
