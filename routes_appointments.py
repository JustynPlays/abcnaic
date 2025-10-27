from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from functools import wraps

# Create blueprint
appointments_bp = Blueprint('appointments', __name__)

def init_appointments_routes(app, get_db):

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

    # Appointments List
    @appointments_bp.route('/appointments')
    @admin_required
    def list_appointments():
        conn = get_db_connection()
        c = conn.cursor()

        # Filtering logic
        query = '''
            SELECT a.*, u.name as user_name
            FROM appointments a
            JOIN users u ON a.user_id = u.id
        '''
        filters = []
        params = []

        if request.args.get('patient_name'):
            filters.append('a.patient_name LIKE ?')
            params.append(f"%{request.args.get('patient_name')}%")
        if request.args.get('service'):
            filters.append('a.service = ?')
            params.append(request.args.get('service'))
        if request.args.get('status'):
            filters.append('a.status = ?')
            params.append(request.args.get('status'))
        if request.args.get('start_date'):
            filters.append('a.appointment_date >= ?')
            params.append(request.args.get('start_date'))
        if request.args.get('end_date'):
            filters.append('a.appointment_date <= ?')
            params.append(request.args.get('end_date'))

        if filters:
            query += ' WHERE ' + ' AND '.join(filters)

        query += ' ORDER BY a.appointment_date DESC, a.appointment_time DESC'

        c.execute(query, params)
        appointments = [dict(row) for row in c.fetchall()]

        # Fetch services for filter dropdown
        c.execute('SELECT name FROM services WHERE is_active = 1 ORDER BY name')
        services = [row['name'] for row in c.fetchall()]

        conn.close()
        return render_template('appointments/list.html', appointments=appointments, services=services)

    # View Appointment Details
    @appointments_bp.route('/appointments/view/<int:appointment_id>')
    @admin_required
    def view_appointment(appointment_id):
        conn = get_db_connection()
        c = conn.cursor()

        # Get appointment details with user info
        c.execute('''
            SELECT a.*, u.name as user_name, u.email as user_email
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = ?
        ''', (appointment_id,))

        appointment = dict(c.fetchone())
        # Load SMS templates for modal selector
        try:
            from utils.sms_templates import get_templates
            sms_templates = get_templates()
        except Exception:
            sms_templates = {}
        # Load available categories from services table for category updates
        try:
            c.execute('SELECT DISTINCT category FROM services WHERE category IS NOT NULL AND category != ""')
            categories = [row['category'] for row in c.fetchall()]
        except Exception:
            categories = []
        conn.close()

        if not appointment:
            flash('Appointment not found.', 'danger')
            return redirect(url_for('appointments.list_appointments'))

        return render_template('appointments/view.html', appointment=appointment, sms_templates=sms_templates, categories=categories)
    @appointments_bp.route('/appointments/manage', methods=['GET', 'POST'])
    @appointments_bp.route('/appointments/manage/<int:appointment_id>', methods=['GET', 'POST'])
    @admin_required
    def manage_appointment(appointment_id=None):
        conn = get_db_connection()
        c = conn.cursor()
        appointment = None
        if appointment_id:
            c.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,))
            appointment = dict(c.fetchone())

            # Prevent editing of completed appointments
            if appointment and appointment.get('status') == 'completed':
                conn.close()
                flash('Cannot edit a completed appointment.', 'danger')
                return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

        if request.method == 'POST':
            patient_name = request.form['patient_name']
            patient_phone = request.form['patient_phone']
            service = request.form['service']
            price = float(request.form['price'])
            appointment_date = request.form['appointment_date']
            appointment_time = request.form['appointment_time']
            current_time = datetime.now().isoformat()

            # Location & Category Information
            bite_location = request.form.get('bite_location', '')
            category = request.form.get('category', '')

            if appointment_id:
                # Check if appointment can be edited (not completed)
                if appointment.get('status') == 'completed':
                    conn.close()
                    flash('Cannot edit a completed appointment.', 'danger')
                    return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

                # Update existing appointment
                c.execute('''
                    UPDATE appointments
                    SET patient_name = ?, patient_phone = ?, service = ?, price = ?,
                        appointment_date = ?, appointment_time = ?, updated_at = ?,
                        bite_location = ?, category = ?
                    WHERE id = ?
                ''', (patient_name, patient_phone, service, price, appointment_date, 
                      appointment_time, current_time, bite_location, category, appointment_id))
                flash('Appointment updated successfully!', 'success')
            else:
                # For new appointments, we need a user_id - this should be handled by the booking system
                # For now, set a default user_id or handle this appropriately
                user_id = 1  # Default user ID - this should be improved based on your needs

                c.execute('''
                    INSERT INTO appointments (user_id, patient_name, patient_phone, service, price, 
                                            appointment_date, appointment_time, status, created_at, updated_at,
                                            bite_location, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                ''', (user_id, patient_name, patient_phone, service, price, appointment_date, 
                      appointment_time, current_time, current_time, bite_location, category))
                flash('Appointment added successfully!', 'success')
            
            conn.commit()
            conn.close()
            return redirect(url_for('appointments.list_appointments'))

        # Fetch data for form dropdowns
        c.execute('SELECT id, name, price FROM services WHERE is_active = 1 ORDER BY name')
        services = c.fetchall()
        conn.close()
        return render_template('appointments/manage.html', appointment=appointment, services=services)

    # Update Appointment Status
    @appointments_bp.route('/appointments/update_status/<int:appointment_id>', methods=['POST'])
    @admin_required
    def update_appointment_status(appointment_id):
        conn = get_db_connection()
        c = conn.cursor()
        status = request.form.get('status')

        # First check current status of the appointment
        c.execute('SELECT status FROM appointments WHERE id = ?', (appointment_id,))
        current_appointment = c.fetchone()

        if not current_appointment:
            conn.close()
            flash('Appointment not found.', 'danger')
            return redirect(url_for('appointments.list_appointments'))

        current_status = current_appointment[0]

        # Prevent status changes for completed appointments
        if current_status == 'completed':
            conn.close()
            flash('Cannot update status of a completed appointment.', 'danger')
            return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

        if status in ['confirmed', 'completed', 'cancelled']:
            c.execute('UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?',
                      (status, datetime.now().isoformat(), appointment_id))
            conn.commit()
            flash(f'Appointment status updated to {status}.', 'success')
        else:
            flash('Invalid status.', 'danger')
        conn.close()
        return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

    @appointments_bp.route('/appointments/update_category/<int:appointment_id>', methods=['POST'])
    @admin_required
    def update_appointment_category(appointment_id):
        conn = get_db_connection()
        c = conn.cursor()
        category = request.form.get('category')

        # Check appointment exists
        c.execute('SELECT status FROM appointments WHERE id = ?', (appointment_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            flash('Appointment not found.', 'danger')
            return redirect(url_for('appointments.list_appointments'))

        current_status = row[0]
        if current_status == 'completed':
            conn.close()
            flash('Cannot update category of a completed appointment.', 'danger')
            return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

        # Update category
        try:
            c.execute('UPDATE appointments SET category = ?, updated_at = ? WHERE id = ?',
                      (category, datetime.now().isoformat(), appointment_id))
            conn.commit()
            flash(f'Appointment category updated to {category}.', 'success')
        except Exception:
            conn.rollback()
            flash('Failed to update category.', 'danger')
        finally:
            conn.close()

        return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

    @appointments_bp.route('/appointments/send_sms/<int:appointment_id>', methods=['POST'])
    @admin_required
    def send_sms_notification(appointment_id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT a.*, u.name as user_name, u.email as user_email FROM appointments a JOIN users u ON a.user_id = u.id WHERE a.id = ?', (appointment_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            flash('Appointment not found.', 'danger')
            return redirect(url_for('appointments.list_appointments'))

        appointment = dict(row)
        # phone may be stored on appointment or user; prefer patient_phone then user phone if exists
        phone = appointment.get('patient_phone') or appointment.get('user_phone')
        if not phone:
            conn.close()
            flash('No phone number available for this appointment.', 'danger')
            return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

        # Backwards-compatible: support legacy message_type form value OR new template_key selection
        message_type = request.form.get('message_type')
        template_key = request.form.get('template_key')
        custom_message = request.form.get('custom_message', '').strip()

        body = None

        # If template_key is provided and not the placeholder, try to load template
        if template_key and template_key != '__none__':
            if template_key == '__custom__':
                if custom_message:
                    body = custom_message
                else:
                    body = None
            else:
                try:
                    from utils.sms_templates import get_templates
                    templates = get_templates()
                    tpl = templates.get(template_key)
                    if tpl:
                        # render simple {{var}} placeholders from appointment and form
                        ctx = {
                            'appointment_date': appointment.get('appointment_date'),
                            'appointment_time': appointment.get('appointment_time'),
                            'new_date': request.form.get('new_date') or appointment.get('appointment_date'),
                            'new_time': request.form.get('new_time') or appointment.get('appointment_time')
                        }
                        text = tpl.get('body', '')
                        for k, v in ctx.items():
                            text = text.replace('{{' + k + '}}', str(v))
                            text = text.replace('{{ ' + k + ' }}', str(v))
                        body = text
                except Exception:
                    body = None

        # Fallback to legacy message_type handling if no template produced
        if not body:
            if message_type == 'cancellation':
                body = f"Your appointment on {appointment.get('appointment_date')} at {appointment.get('appointment_time')} has been cancelled. Please contact us if you need to reschedule."
            elif message_type == 'reschedule':
                # Optionally accept new_date/new_time from form
                new_date = request.form.get('new_date') or appointment.get('appointment_date')
                new_time = request.form.get('new_time') or appointment.get('appointment_time')
                body = f"Your appointment has been rescheduled to {new_date} at {new_time}. Please contact us if this does not work."
            elif message_type == 'custom' and custom_message:
                body = custom_message

        if not body:
            conn.close()
            flash('Invalid message selection.', 'danger')
            return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

        # Send via utils.sms if available
        try:
            from utils.sms import send_message
            result = send_message(phone, body)
            if result.get('ok'):
                flash('SMS sent successfully.', 'success')
            else:
                flash(f"Failed to send SMS: {result.get('error')}", 'danger')
        except Exception as e:
            flash(f'Error sending SMS: {e}', 'danger')

        conn.close()
        return redirect(url_for('appointments.view_appointment', appointment_id=appointment_id))

    @appointments_bp.route('/appointments/export')
    @admin_required
    def export_appointments():
        conn = get_db_connection()
        c = conn.cursor()

        query = '''
            SELECT a.id, a.appointment_date, a.appointment_time, a.patient_name, a.service, u.name as user_name, a.status, a.updated_at
            FROM appointments a
            JOIN users u ON a.user_id = u.id
        '''
        filters = []
        params = []

        if request.args.get('patient_name'):
            filters.append('a.patient_name LIKE ?')
            params.append(f"%{request.args.get('patient_name')}%")
        if request.args.get('service'):
            filters.append('a.service = ?')
            params.append(request.args.get('service'))
        if request.args.get('status'):
            filters.append('a.status = ?')
            params.append(request.args.get('status'))
        if request.args.get('start_date'):
            filters.append('a.appointment_date >= ?')
            params.append(request.args.get('start_date'))
        if request.args.get('end_date'):
            filters.append('a.appointment_date <= ?')
            params.append(request.args.get('end_date'))

        if filters:
            query += ' WHERE ' + ' AND '.join(filters)

        query += ' ORDER BY a.appointment_date DESC, a.appointment_time DESC'

        c.execute(query, params)
        appointments = c.fetchall()
        conn.close()

        import io
        import csv
        from flask import Response

        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['ID', 'Date', 'Time', 'Patient Name', 'Service', 'Booked By', 'Status', 'Date Completed'])

        for row in appointments:
            row_dict = dict(row)
            date_completed = row_dict['updated_at'] if row_dict['status'] == 'completed' else 'N/A'
            writer.writerow([row_dict['id'], row_dict['appointment_date'], row_dict['appointment_time'], row_dict['patient_name'], row_dict['service'], row_dict['user_name'], row_dict['status'], date_completed])

        output.seek(0)
        return Response(output, mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=appointments.csv"})


    # SMS Templates management
    @appointments_bp.route('/sms_templates', methods=['GET', 'POST'])
    @admin_required
    def manage_sms_templates():
        try:
            from utils.sms_templates import get_templates, save_templates
        except Exception:
            flash('SMS templates backend not available.', 'danger')
            return redirect(url_for('appointments.list_appointments'))

        if request.method == 'POST':
            # Expect form fields like title_<key> and body_<key>
            templates = get_templates()
            for key in list(templates.keys()):
                title = request.form.get(f'title_{key}', templates[key].get('title'))
                body = request.form.get(f'body_{key}', templates[key].get('body'))
                templates[key]['title'] = title
                templates[key]['body'] = body
            # allow adding a new template
            new_key = request.form.get('new_key', '').strip()
            new_title = request.form.get('new_title', '').strip()
            new_body = request.form.get('new_body', '').strip()
            if new_key and new_body:
                templates[new_key] = {'title': new_title or new_key, 'body': new_body}
            save_templates(templates)
            flash('SMS templates updated.', 'success')
            return redirect(url_for('appointments.manage_sms_templates'))

        templates = get_templates()
        return render_template('admin/sms_templates.html', templates=templates)

    app.register_blueprint(appointments_bp, url_prefix='/admin')
