from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from functools import wraps

# Create blueprint
services_bp = Blueprint('services', __name__)

def init_services_routes(app, get_db):

    def get_db_connection():
        return get_db()

    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' not in session:
                flash('Please log in as admin to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    # Services List
    @services_bp.route('/services')
    @admin_required
    def list_services():
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM services ORDER BY category, name')
        services = [dict(row) for row in c.fetchall()]
        conn.close()
        return render_template('services/list.html', services=services)

    # Add/Edit Service
    @services_bp.route('/services/manage', methods=['GET', 'POST'])
    @services_bp.route('/services/manage/<int:service_id>', methods=['GET', 'POST'])
    @admin_required
    def manage_service(service_id=None):
        conn = get_db_connection()
        c = conn.cursor()
        service = None
        if service_id:
            c.execute('SELECT * FROM services WHERE id = ?', (service_id,))
            service = dict(c.fetchone())

        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            category = request.form['category']
            price = float(request.form['price'])
            duration = int(request.form['duration_minutes'])
            is_active = 1 if 'is_active' in request.form else 0
            current_time = datetime.now().isoformat()

            if service_id:
                # Update existing service
                c.execute('''
                    UPDATE services
                    SET name = ?, description = ?, category = ?, price = ?, duration_minutes = ?, is_active = ?, updated_at = ?
                    WHERE id = ?
                ''', (name, description, category, price, duration, is_active, current_time, service_id))
                flash('Service updated successfully!', 'success')
            else:
                # Add new service
                c.execute('''
                    INSERT INTO services (name, description, category, price, duration_minutes, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, description, category, price, duration, is_active, current_time, current_time))
                flash('Service added successfully!', 'success')
            
            conn.commit()
            conn.close()
            return redirect(url_for('services.list_services'))

        conn.close()
        return render_template('services/manage.html', service=service)

    # Delete Service
    @services_bp.route('/services/delete/<int:service_id>', methods=['POST'])
    @admin_required
    def delete_service(service_id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM services WHERE id = ?', (service_id,))
        conn.commit()
        conn.close()
        flash('Service deleted successfully!', 'danger')
        return redirect(url_for('services.list_services'))

    app.register_blueprint(services_bp, url_prefix='/admin')
