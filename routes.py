from flask import render_template, request, redirect, url_for, session, flash, current_app, abort, send_file, make_response, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from datetime import datetime, timedelta
import sqlite3
import os
import re
from io import BytesIO
from io import StringIO
import csv
from utils.pdf_generator import generate_vaccine_record_pdf
from functools import wraps
import json

def get_missing_password_requirements(password):
    """
    Returns a list of missing password requirements for feedback.
    """
    import re
    missing = []
    if len(password) < 8:
        missing.append('at least 8 characters')
    if not re.search(r'[A-Z]', password):
        missing.append('an uppercase letter')
    if not re.search(r'[a-z]', password):
        missing.append('a lowercase letter')
    if not re.search(r'\d', password):
        missing.append('a number')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?]', password):
        missing.append('a special character')
    return missing

def validate_age(date_of_birth):
    """
    Validate that user is at least 13 years old
    """
    from datetime import datetime

    try:
        birth_date = datetime.strptime(date_of_birth, '%Y-%m-%d')
        today = datetime.now()

        # Calculate age more accurately
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1

        return age >= 13
    except ValueError:
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def init_routes(app, get_db, mail, serializer):
    # Store the get_db function in app context for use in routes
    app.get_db = get_db
    app.mail = mail
    app.serializer = serializer
    
    # Admin credentials (in a real app, store these in environment variables or a config file)
    ADMIN_CREDENTIALS = {
        'username': 'admin',
        'password': 'admin123'  # In production, use environment variables and hash the password
    }
    
    # Session key for admin
    ADMIN_SESSION_KEY = 'admin_logged_in'

    # Admin authentication decorator
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip admin check for non-admin routes
            if not request.path.startswith('/admin'):
                return f(*args, **kwargs)
                
            # Check admin session
            if not session.get(ADMIN_SESSION_KEY):
                flash('Please log in as admin to access this page.', 'danger')
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
    # Email verification removed: users are active immediately after registration.
    @app.route('/admin/faq')
    @admin_required
    def admin_faq():
        conn = get_db()
        c = conn.cursor()

        # Get all FAQs ordered by display_order
        c.execute('''
            SELECT * FROM faq
            ORDER BY display_order, created_at DESC
        ''')
        faqs = [dict(row) for row in c.fetchall()]

        # If there are no FAQs yet, seed a small set of useful defaults so admins can edit them
        if not faqs:
            defaults = [
                ('What should I bring to my appointment?', 'Please bring a valid ID, your vaccination card (if any), and any relevant medical records.', 'general', 1),
                ('Do you accept walk-ins?', 'We prioritize scheduled appointments — walk-ins are accepted only when capacity allows.', 'appointments', 2),
                ('What are your clinic hours?', 'We are open Monday to Saturday, 8:00 AM to 5:00 PM. Please check for holiday announcements.', 'general', 3),
                ('How much does the Anti-Rabies vaccine cost?', 'Pricing may vary. Please check the Services & Fees section or contact the clinic for current prices.', 'services', 4),
                ('Can I cancel or reschedule my appointment?', 'Yes — you may cancel or reschedule through your account dashboard up to 24 hours before the appointment.', 'appointments', 5),
                ('How do I change my appointment details?', 'You can update your appointment details from the My Bookings page. If you need assistance, contact the clinic directly.', 'appointments', 6),
                ('What payment methods are accepted?', 'We accept cash and major debit/credit cards. For specific services, payments may be collected at the clinic.', 'payments', 7),
                ('Will I receive reminders for vaccine schedules?', 'If you opt in for reminders, we will notify you about follow-up vaccine schedules. Check your profile settings.', 'general', 8),
                ('What should I do after animal bites?', 'Immediately clean the wound with soap and water, seek medical evaluation, and report the incident to your local clinic for rabies risk assessment.', 'emergency', 9),
                ('Is there parking available?', 'Yes — limited parking is available on site. Public transportation options are also nearby.', 'general', 10),
                ('Which documents are required for minors?', 'A parent or guardian must accompany minors and bring a valid ID for both parent and minor. Consent forms may be required.', 'requirements', 11),
                ('Who do I contact for urgent questions?', 'For urgent inquiries, call the clinic hotline during working hours. For life-threatening emergencies, call local emergency services first.', 'contact', 12),
            ]
            try:
                for q, a, cat, order in defaults:
                    c.execute('INSERT INTO faq (question, answer, category, display_order, is_active, created_at) VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)', (q, a, cat, order))
                conn.commit()
                # Re-fetch faqs
                c.execute('SELECT * FROM faq ORDER BY display_order, created_at DESC')
                faqs = [dict(row) for row in c.fetchall()]
            except Exception:
                conn.rollback()

        # Get FAQ categories for filtering
        c.execute('SELECT DISTINCT category FROM faq ORDER BY category')
        categories = [row['category'] for row in c.fetchall()]

        conn.close()

        return render_template('admin_faq.html', faqs=faqs, categories=categories)

    @app.route('/admin/faq/add', methods=['GET', 'POST'])
    @admin_required
    def admin_add_faq():
        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            answer = request.form.get('answer', '').strip()
            category = request.form.get('category', 'general').strip()
            display_order = request.form.get('display_order', 0, type=int)

            if not question or not answer:
                flash('Question and answer are required.', 'danger')
                return redirect(url_for('admin_add_faq'))

            conn = get_db()
            c = conn.cursor()

            try:
                c.execute('''
                    INSERT INTO faq (question, answer, category, display_order, is_active)
                    VALUES (?, ?, ?, ?, 1)
                ''', (question, answer, category, display_order))

                conn.commit()
                flash('FAQ added successfully!', 'success')
                return redirect(url_for('admin_faq'))

            except Exception as e:
                conn.rollback()
                flash('Error adding FAQ. Please try again.', 'danger')
            finally:
                conn.close()

        # Get available categories for dropdown
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT DISTINCT category FROM faq ORDER BY category')
        categories = [row['category'] for row in c.fetchall()]
        conn.close()

        # If no categories exist yet, use default ones
        if not categories:
            categories = ['general', 'emergency', 'services', 'appointments', 'requirements', 'contact']

        return render_template('admin_faq_form.html', faq=None, categories=categories)

    @app.route('/admin/faq/edit/<int:faq_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_faq(faq_id):
        conn = get_db()
        c = conn.cursor()

        # Get the FAQ to edit
        c.execute('SELECT * FROM faq WHERE id = ?', (faq_id,))
        faq = c.fetchone()

        if not faq:
            flash('FAQ not found.', 'danger')
            return redirect(url_for('admin_faq'))

        faq = dict(faq)

        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            answer = request.form.get('answer', '').strip()
            category = request.form.get('category', 'general').strip()
            display_order = request.form.get('display_order', 0, type=int)
            is_active = 1 if request.form.get('is_active') else 0

            if not question or not answer:
                flash('Question and answer are required.', 'danger')
                return redirect(url_for('admin_edit_faq', faq_id=faq_id))

            try:
                c.execute('''
                    UPDATE faq
                    SET question = ?, answer = ?, category = ?, display_order = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (question, answer, category, display_order, is_active, faq_id))

                conn.commit()
                flash('FAQ updated successfully!', 'success')
                return redirect(url_for('admin_faq'))

            except Exception as e:
                conn.rollback()
                flash('Error updating FAQ. Please try again.', 'danger')

        # Get available categories for dropdown
        c.execute('SELECT DISTINCT category FROM faq WHERE id != ? ORDER BY category', (faq_id,))
        categories = [row['category'] for row in c.fetchall()]

        # Add current FAQ's category if not in the list
        if faq['category'] not in categories:
            categories.append(faq['category'])

        categories.sort()

        conn.close()

        return render_template('admin_faq_form.html', faq=faq, categories=categories)
    @app.route('/check-username', methods=['POST'])
    def check_username():
        try:
            data = request.get_json()
            username = data.get('username', '').strip()

            if not username:
                return jsonify({'available': False, 'error': 'Username is required'})

            # Validate username format (3-30 characters, letters, numbers, underscores only)
            import re
            if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
                return jsonify({'available': False, 'error': 'Invalid username format'})

            # Check if username exists in database
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE username = ?', (username,))
            existing_user = c.fetchone()
            conn.close()

            if existing_user:
                return jsonify({'available': False})
            else:
                return jsonify({'available': True})

        except Exception as e:
            return jsonify({'available': False, 'error': 'Server error'})

    @app.route('/check-email', methods=['POST'])
    def check_email():
        try:
            data = request.get_json()
            email = data.get('email', '').strip()

            if not email:
                return jsonify({'available': False, 'error': 'Email is required'})

            # Basic email format validation
            import re
            if not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
                return jsonify({'available': False, 'error': 'Invalid email format'})

            # Check if email exists in database
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            existing_user = c.fetchone()
            conn.close()

            if existing_user:
                return jsonify({'available': False})
            else:
                return jsonify({'available': True})

        except Exception as e:
            current_app.logger.error(f'Error in check_email: {e}')
            return jsonify({'available': False, 'error': 'Server error'})
    
    @app.route('/')
    def index():
        """Root route that renders the landing page"""
        return render_template('landing.html')

    @app.route('/home')
    @login_required
    def home():
        conn = get_db()
        c = conn.cursor()
        user_id = session.get('user_id')
        
        # Get user data from database
        c.execute('SELECT name, username, email FROM users WHERE id = ?', (user_id,))
        user_data = c.fetchone()
        conn.close()
        
        # Store user data in session for the template
        if user_data:
            session['user_name'] = user_data['name']
            session['user_username'] = user_data['username']  # Also store username
            session['user_email'] = user_data['email']
            
        return render_template('home.html')

    @app.route('/virtual-vaccine-card')
    @login_required
    def virtual_vaccine_card():
        """
        Render a virtual vaccination card page for the logged-in user.
        Uses session values populated on /home for basic user info. The template
        can be enhanced later to pull more fields from the database.
        """
        user = {
            'name': session.get('user_name', ''),
            'username': session.get('user_username', ''),
            'email': session.get('user_email', ''),
        }

        # Detect common icon files in static/icons and pass their URLs to the template.
        icons = {}
        possible_icons = {
            'phone': ['phone.png', 'phone.svg', 'tel.png', 'call.png'],
            'facebook': ['facebook.png', 'fb.png', 'facebook.svg'],
            'location': ['location.png', 'map.png', 'pin.png', 'location.svg'],
            'badge': ['cover.png', 'badge.png', 'logo-badge.png', 'consult.png']
        }

        for key, names in possible_icons.items():
            for name in names:
                path = os.path.join(current_app.root_path, 'static', 'icons', name)
                if os.path.exists(path):
                    icons[key] = url_for('static', filename=f'icons/{name}')
                    break

        return render_template('virtual_vaccine_card.html', user=user, icons=icons)

    @app.route('/virtual-vaccine-card/back')
    @login_required
    def virtual_vaccine_card_back():
        """
        Render the back of the virtual vaccination card. Mirrors the front page's
        header/sidebar and provides the detailed exposure and prophylaxis tables.
        """
        user = {
            'name': session.get('user_name', ''),
            'username': session.get('user_username', ''),
            'email': session.get('user_email', ''),
        }

        # reuse icons detection (same as front)
        icons = {}
        possible_icons = {
            'phone': ['phone.png', 'phone.svg', 'tel.png', 'call.png'],
            'facebook': ['facebook.png', 'fb.png', 'facebook.svg'],
            'location': ['location.png', 'map.png', 'pin.png', 'location.svg'],
            'badge': ['cover.png', 'badge.png', 'logo-badge.png', 'consult.png']
        }

        for key, names in possible_icons.items():
            for name in names:
                path = os.path.join(current_app.root_path, 'static', 'icons', name)
                if os.path.exists(path):
                    icons[key] = url_for('static', filename=f'icons/{name}')
                    break

        return render_template('virtual_vaccine_card_back.html', user=user, icons=icons)

    @app.route('/cardicons/<path:filename>')
    def cardicons(filename):
        """Serve icons from the project's icons/cardicons folder."""
        directory = os.path.join(current_app.root_path, 'icons', 'cardicons')
        return send_from_directory(directory, filename)
    @app.route('/faq')
    def faq():
        conn = get_db()
        c = conn.cursor()

        # Get active FAQs ordered by display_order
        c.execute('''
            SELECT question, answer, category
            FROM faq
            WHERE is_active = 1
            ORDER BY display_order, created_at
        ''')
        faqs = [dict(row) for row in c.fetchall()]

        # If no public FAQs exist yet, insert a helpful default set so visitors see useful information.
        # This mirrors the admin seeding but is a temporary fallback for the public FAQ page.
        if not faqs:
            defaults = [
                ('What should I bring to my appointment?', 'Please bring a valid ID, your vaccination card (if any), and any relevant medical records.', 'general', 1),
                ('Do you accept walk-ins?', 'We prioritize scheduled appointments — walk-ins are accepted only when capacity allows.', 'appointments', 2),
                ('What are your clinic hours?', 'We are open Monday to Saturday, 8:00 AM to 5:00 PM. Please check for holiday announcements.', 'general', 3),
                ('How much does the Anti-Rabies vaccine cost?', 'Pricing may vary. Please check the Services & Fees section or contact the clinic for current prices.', 'services', 4),
                ('Can I cancel or reschedule my appointment?', 'Yes — you may cancel or reschedule through your account dashboard up to 24 hours before the appointment.', 'appointments', 5),
                ('What payment methods are accepted?', 'We accept cash and major debit/credit cards. For specific services, payments may be collected at the clinic.', 'payments', 6),
                ('Will I receive reminders for vaccine schedules?', 'If you opt in for reminders, we will notify you about follow-up vaccine schedules. Check your profile settings.', 'general', 7),
                ('What should I do after animal bites?', 'Immediately clean the wound with soap and water, seek medical evaluation, and report the incident to your local clinic for rabies risk assessment.', 'emergency', 8),
                ('Is there parking available?', 'Yes — limited parking is available on site. Public transportation options are also nearby.', 'general', 9),
                ('Which documents are required for minors?', 'A parent or guardian must accompany minors and bring a valid ID for both parent and minor. Consent forms may be required.', 'requirements', 10),
                ('Who do I contact for urgent questions?', 'For urgent inquiries, call the clinic hotline during working hours. For life-threatening emergencies, call local emergency services first.', 'contact', 11),
            ]
            try:
                for q, a, cat, order in defaults:
                    c.execute('INSERT INTO faq (question, answer, category, display_order, is_active, created_at) VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)', (q, a, cat, order))
                conn.commit()
                c.execute('''
                    SELECT question, answer, category
                    FROM faq
                    WHERE is_active = 1
                    ORDER BY display_order, created_at
                ''')
                faqs = [dict(row) for row in c.fetchall()]
            except Exception:
                conn.rollback()
        conn.close()

        return render_template('faq.html', faqs=faqs)

    @app.route('/book-appointment', methods=['GET', 'POST'])
    @login_required
    def book_appointment():
        # New: show appointment type selection on GET. On POST, save type and redirect to services page.
        if request.method == 'POST':
            appointment_type = request.form.get('appointment_type')
            # Keep existing session details if present, else initialize
            details = session.get('appointment_details', {})
            details.update({'appointment_type': appointment_type})
            # Clear any previously-selected service/price/date/time when changing type
            # This prevents stale selections from a previous flow (e.g., going back) from
            # being reused and causing the flow to skip steps.
            for key in ('service', 'price', 'date', 'time', 'category', 'animal_type', 'exposure_type', 'bite_location', 'exposure_details'):
                details.pop(key, None)
            session['appointment_details'] = details
            # Debug log
            print(f"DEBUG [book_appointment POST]: saved appointment_type={appointment_type}, session now={session.get('appointment_details')}")
            # If consultation was selected, skip Services & Fees and go straight to datetime.
            # Set safe defaults for service/category/price so downstream steps that expect these
            # keys have predictable values.
            if appointment_type == 'consultation':
                # Treat internal 'consultation' flow as Booster Vaccine selection for UX.
                # Default the chosen service to Anti-Rabies Vaccine with standard price.
                details.update({
                    'service': 'Anti-Rabies Vaccine',
                    'price': '₱425.00',
                    'category': 'Vaccination'
                })
                session['appointment_details'] = details
                print(f"DEBUG [book_appointment POST]: consultation selected, skipping services, session now={session.get('appointment_details')}")
                return redirect(url_for('book_appointment_datetime'))

            return redirect(url_for('book_appointment_services'))

        return render_template('book_appointment_type.html')

    @app.route('/book-appointment/services', methods=['GET', 'POST'])
    @login_required
    def book_appointment_services():
        # This route contains the previous booking logic (services selection and storing service price)
        if request.method == 'POST':
            # Debug log incoming form and session
            print(f"DEBUG [book_appointment_services POST]: form={dict(request.form)}")
            print(f"DEBUG [book_appointment_services POST]: session before processing={session.get('appointment_details')}")
            # Get service price from database
            conn = get_db()
            c = conn.cursor()
            # Read form fields we need
            # Support multiple service inputs (checkboxes) when appointment_type is 'vaccination'
            selected_services = request.form.getlist('service') if request.form else []
            animal_type = request.form.get('animal_type')
            animal_etc_text = request.form.get('animal_etc_text')
            exposure_type = request.form.get('exposure_type')
            bite_location = request.form.get('body_diagram_selection', '')
            exposure_details = request.form.get('exposure_details')
            category = request.form.get('category')

            # Prepare fallback price map
            service_prices = {
                'Anti-Rabies Vaccine': 425.00,
                'Tetanus Toxoid': 150.00,
                'ERIG Vaccine': 1200.00,
                'Wound Care': 300.00,
                'Follow-up Consultation': 250.00,
                # keep the previous fallback for unknown
            }

            applied_services = []
            total = 0.0

            # If this flow is for vaccination, ensure mandatory vaccines are applied
            details = session.get('appointment_details', {})
            appointment_type = details.get('appointment_type')

            # Helper to get price from DB or fallback
            def get_price_for(name):
                try:
                    c.execute('SELECT price FROM services WHERE name = ? AND is_active = 1', (name,))
                    row = c.fetchone()
                    if row:
                        return float(row[0])
                except Exception:
                    pass
                return float(service_prices.get(name, 0.0))

            # For vaccination flows, always include Anti-Rabies and Tetanus
            if appointment_type == 'vaccination':
                for mandatory in ('Anti-Rabies Vaccine', 'Tetanus Toxoid'):
                    price = get_price_for(mandatory)
                    applied_services.append(mandatory)
                    total += price

                # If bite location contains 'head' (case-insensitive), also apply ERIG Vaccine
                if bite_location and 'head' in bite_location.lower():
                    erig_price = get_price_for('ERIG Vaccine')
                    applied_services.append('ERIG Vaccine')
                    total += erig_price

                # Additionally, include any services the user manually selected (may be multiple checkboxes)
                if selected_services:
                    for sel in selected_services:
                        if sel and sel not in applied_services:
                            applied_services.append(sel)
                            total += get_price_for(sel)

            else:
                # Non-vaccination: require a single selected service from form
                if not selected_services or len(selected_services) == 0:
                    flash('Please select a service before continuing.', 'danger')
                    print(f"DEBUG [book_appointment_services POST]: no service selected in form; redirecting back to services")
                    conn.close()
                    return redirect(url_for('book_appointment_services'))

                # For consultation flows, we expect a single service (radio). If multiple were sent, take the first.
                selected_service = selected_services[0]
                applied_services.append(selected_service)
                total += get_price_for(selected_service)

            # Format the price and store combined service string
            formatted_price = f'₱{total:,.2f}'
            service_str = ', '.join(applied_services) if applied_services else (', '.join(selected_services) or 'No service selected')

            # Merge into session
            details.update({
                'animal_type': animal_type,
                'animal_etc_text': animal_etc_text,
                'exposure_type': exposure_type,
                'bite_location': bite_location,
                'exposure_details': exposure_details,
                'category': category or (details.get('category') if details else None),
                'service': service_str,
                'price': formatted_price
            })
            session['appointment_details'] = details
            conn.close()
            print(f"DEBUG [book_appointment_services POST]: stored details={session.get('appointment_details')}")
            return redirect(url_for('book_appointment_datetime'))

        # GET request - fetch services from database
        # Safety: if appointment_type is consultation, this page should be skipped.
        details = session.get('appointment_details', {})
        if details.get('appointment_type') == 'consultation':
            print(f"DEBUG [book_appointment_services GET]: appointment_type is consultation; redirecting to datetime. session={details}")
            return redirect(url_for('book_appointment_datetime'))

        conn = get_db()
        c = conn.cursor()

        # Get active services categorized
        c.execute('''
            SELECT name, category, price, duration_minutes
            FROM services
            WHERE is_active = 1
            ORDER BY category, name
        ''')
        services = [dict(row) for row in c.fetchall()]

        # Categorize services
        vaccination_services = [s for s in services if s['category'].lower() == 'vaccination']
        consultation_services = [s for s in services if s['category'].lower() == 'consultation']

        conn.close()
        # Debug log session when rendering services page
        print(f"DEBUG [book_appointment_services GET]: session={session.get('appointment_details')}")

        return render_template('book_appointment.html',
                             services=services,
                             vaccination_services=vaccination_services,
                             consultation_services=consultation_services)

    @app.route('/book-appointment/datetime', methods=['GET', 'POST'])
    @login_required
    def book_appointment_datetime():
        if request.method == 'POST':
            # Store date and time in session
            if 'appointment_details' in session:
                # Preserve existing details and add new ones
                details = session.get('appointment_details', {})
                details.update({
                    'date': request.form.get('selected_date'),
                    'time': request.form.get('selected_time')
                })
                session['appointment_details'] = details
            # Redirect to the next step (details page - to be created)
            return redirect(url_for('appointment_details'))
        return render_template('book_appointment_datetime.html')

    @app.route('/book-appointment/details', methods=['GET', 'POST'])
    @login_required
    def appointment_details():
        if request.method == 'POST':
            if 'appointment_details' in session:
                # Preserve existing details and add new ones
                details = session.get('appointment_details', {})
                # Read date_of_birth from form and compute age server-side
                dob_str = request.form.get('date_of_birth')
                age_val = None
                if dob_str:
                    try:
                        from datetime import datetime, date
                        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                        today = date.today()
                        # Compute age in years
                        age_val = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    except Exception as e:
                        print(f"DEBUG: failed to parse DOB '{dob_str}': {e}")
                        dob = None
                else:
                    dob = None

                details.update({
                    'name': request.form.get('name'),
                    'address': request.form.get('address'),
                    # store both dob (ISO string) and computed age
                    'date_of_birth': dob_str,
                    'age': str(age_val) if age_val is not None else request.form.get('age'),
                    'gender': request.form.get('gender'),
                    'phone': request.form.get('phone'),
                    'branch': request.form.get('branch'),
                    'email': request.form.get('email')
                })
                session['appointment_details'] = details
                # Placeholder for summary page
                flash('Details saved successfully!', 'success')
                return redirect(url_for('appointment_summary'))
        return render_template('appointment_details.html')

    @app.route('/book-appointment/summary', methods=['GET', 'POST'])
    @login_required
    def appointment_summary():
        if 'appointment_details' not in session or 'user_id' not in session:
            flash('No appointment details found. Please start over.', 'danger')
            return redirect(url_for('book_appointment'))

        if request.method == 'POST':
            try:
                # Debug: Print session data
                print(f"DEBUG: Session appointment_details: {session.get('appointment_details', 'NOT FOUND')}")
                print(f"DEBUG: Session user_id: {session.get('user_id', 'NOT FOUND')}")

                # Get database connection
                conn = get_db()
                c = conn.cursor()

                # Get appointment details from session
                details = session['appointment_details']

                # Debug: Print details that will be inserted
                print(f"DEBUG: Details to insert: {details}")

                # Ensure the appointments table has an animal_etc_text column (backfill safe)
                try:
                    c.execute("PRAGMA table_info(appointments)")
                    cols = [r[1] for r in c.fetchall()]
                except Exception:
                    cols = []
                if 'animal_etc_text' not in cols:
                    try:
                        c.execute("ALTER TABLE appointments ADD COLUMN animal_etc_text TEXT")
                        conn.commit()
                    except Exception:
                        # best-effort: ignore if unable to alter (e.g., permissions); continue
                        pass

                # Insert appointment into database (include animal_etc_text)
                c.execute('''
                    INSERT INTO appointments (
                        user_id, service, appointment_date, appointment_time,
                        patient_name, patient_address, patient_age, patient_gender,
                        patient_phone, branch, patient_email, price, animal_type, animal_etc_text,
                        exposure_type, bite_location, category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session['user_id'],
                    details.get('service', 'Rabies Vaccination'),
                    details.get('date'),
                    details.get('time'),
                    details.get('name'),
                    details.get('address'),
                    int(details.get('age', 0)) if details.get('age') else None,
                    details.get('gender'),
                    details.get('phone'),
                    details.get('branch'),
                    details.get('email'),
                    float(details.get('price', 0).replace('₱', '').replace(',', '')) if details.get('price') else 0.0,
                    details.get('animal_type'),
                    details.get('animal_etc_text'),
                    details.get('exposure_type'),
                    details.get('bite_location', ''),  # New field for body diagram
                    details.get('category')
                ))
                
                # Commit the transaction
                conn.commit()
                
                # Clear the appointment details from session
                session.pop('appointment_details', None)
                
                # Get the appointment ID for the confirmation
                appointment_id = c.lastrowid
                
                # Send SMS confirmation if enabled
                try:
                    from utils.sms_service import send_appointment_confirmation
                    send_appointment_confirmation(appointment_id)
                except Exception as e:
                    # Log error but don't fail the appointment booking
                    current_app.logger.error(f"Error sending SMS confirmation for appointment {appointment_id}: {str(e)}")
                
                # Close the database connection
                conn.close()
                
                flash('Appointment booked successfully! Your reference number is #{}'.format(appointment_id), 'success')
                return redirect(url_for('home'))
                
            except Exception as e:
                # If there's an error, rollback and show error message
                if 'conn' in locals():
                    conn.rollback()
                    conn.close()
                print(f"Error saving appointment: {str(e)}")
                flash('An error occurred while saving your appointment. Please try again.', 'danger')
                return redirect(url_for('appointment_summary'))

        # Prepare a display service string for the summary (show full list including Tetanus)
        details = session.get('appointment_details', {})
        service_display = ''
        try:
            service_display = details.get('service', '') if details else ''
        except Exception:
            service_display = ''

        return render_template('appointment_summary.html', display_service=service_display)

    @app.route('/bite-categories')
    @login_required
    def bite_categories():
        return render_template('bite_categories.html')
        
    @app.route('/animal-bite-first-aid')
    @login_required
    def animal_bite_first_aid():
        return render_template('animal_bite_first_aid.html')
        
    @app.route('/after-care-reminder')
    @login_required
    def after_care_reminder():
        return render_template('after_care_reminder.html')

    @app.route('/first-aid-donts')
    @login_required
    def first_aid_donts():
        return render_template('first_aid_donts.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            identifier = request.form['identifier']  # Can be username or email
            password = request.form['password']
            conn = get_db()
            c = conn.cursor()

            # FIRST: Check if this is an admin login attempt
            if (identifier == ADMIN_CREDENTIALS['username'] and
                password == ADMIN_CREDENTIALS['password']):
                # Admin login successful
                session[ADMIN_SESSION_KEY] = True
                session.permanent = True
                app.permanent_session_lifetime = timedelta(minutes=30)

                # Update last login time (optional for admin)
                next_url = request.args.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect(url_for('admin_dashboard'))

            # SECOND: Check regular user login
            # Try to find user by email or username depending on schema
            try:
                c.execute("PRAGMA table_info(users)")
                cols = [r[1] for r in c.fetchall()]
            except Exception:
                cols = []

            if 'username' in cols:
                # username column exists: search by email OR username
                c.execute('SELECT * FROM users WHERE email = ? OR username = ?', (identifier, identifier))
            else:
                # fallback: only email
                c.execute('SELECT * FROM users WHERE email = ?', (identifier,))
            user = c.fetchone()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                # Allow login immediately without email verification
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_username'] = user['username']  # Store username in session
                session['user_email'] = user['email']

                # Update last login time
                conn = get_db()
                c = conn.cursor()
                c.execute('UPDATE users SET last_login = ? WHERE id = ?',
                         (datetime.now().isoformat(), user['id']))
                conn.commit()
                conn.close()
                next_url = request.args.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect(url_for('home'))
            else:
                flash('Invalid username/email or password.', 'danger')
        return render_template('login.html')

    def logout():
        session.clear()
        flash('Logged out successfully.', 'success')
        return redirect(url_for('login'))

    def send_password_reset_email(email, token):
        with app.app_context():
            link = url_for('reset_password', token=token, _external=True)
            msg = Message('Reset your Animal Bite Center password', recipients=[email])
            msg.body = f'Click the link to reset your password: {link}\nIf you did not request a password reset, please ignore this email.'
            app.mail.send(msg)

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if request.method == 'POST':
            email = request.form['email']
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = c.fetchone()
            
            if not user:
                flash('Email address not found in our system.', 'danger')
                conn.close()
                return render_template('forgot_password.html')
            
            # If passwords are provided, validate and update
            if new_password and confirm_password:
                if new_password != confirm_password:
                    flash('Passwords do not match.', 'danger')
                    conn.close()
                    return render_template('forgot_password.html', show_password_fields=True, email=email)

                missing = get_missing_password_requirements(new_password)
                if missing:
                    # Pass missing requirements to the template for inline display
                    conn.close()
                    return render_template('forgot_password.html', show_password_fields=True, email=email, missing_passwords=missing)

                # Update password
                password_hash = generate_password_hash(new_password)
                c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
                conn.commit()
                conn.close()
                flash('Password reset successfully! You can now login with your new password.', 'success')
                return redirect(url_for('login'))
            else:
                # First step - email verification, show password fields
                conn.close()
                return render_template('forgot_password.html', show_password_fields=True, email=email)
                
        return render_template('forgot_password.html')

    # Old email-based password reset route - no longer needed
    # @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    # def reset_password(token):
    #     try:
    #         email = serializer.loads(token, salt='password-reset', max_age=3600)
    #     except Exception:
    #         flash('Password reset link is invalid or has expired.', 'danger')
    #         return redirect(url_for('forgot_password'))

    #     conn = get_db()
    #     c = conn.cursor()
    #     c.execute('SELECT * FROM users WHERE email = ?', (email,))
    #     user = c.fetchone()
    #     if not user:
    #         flash('User not found.', 'danger')
    #         return redirect(url_for('forgot_password'))

    #     if request.method == 'POST':
    #         password = request.form['password']
    #         confirm_password = request.form['confirm_password']

    #         if password != confirm_password:
    #             flash('Passwords do not match.', 'danger')
    #             return render_template('reset_password.html', token=token)

    #         if not validate_password_strength(password):
    #             flash('Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character.', 'danger')
    #             return render_template('reset_password.html', token=token)

    #         # Update password and clear reset token
    #         password_hash = generate_password_hash(password)
    #         c.execute('UPDATE users SET password_hash = ?, password_reset_token = NULL WHERE email = ?', (password_hash, email))
    #         conn.commit()
    #         flash('Password reset successfully! You can now login with your new password.', 'success')
    #         return redirect(url_for('login'))

    #     conn.close()
    #     return render_template('reset_password.html', token=token)

    # Resend verification route removed because verification is no longer required.

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            first_name = request.form.get('first_name', '')
            last_name = request.form.get('last_name', '')
            username = request.form.get('username', '')
            email = request.form.get('email', '')
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            date_of_birth = request.form.get('date_of_birth')
            gender = request.form.get('gender')
            contact_number = request.form.get('contact_number', '')
            address = request.form.get('address', '')

            # Collect form values to repopulate the form on error
            form_values = {
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'email': email,
                'date_of_birth': date_of_birth,
                'gender': gender,
                'contact_number': contact_number,
                'address': address
            }

            # Validate required fields
            if not all([first_name, last_name, username, email, password, confirm_password, date_of_birth, gender, contact_number, address]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('register.html', **form_values)

            # Validate password strength
            missing = get_missing_password_requirements(password)
            if missing:
                # Do not flash detailed password requirement messages at the top of the page.
                # Instead pass the list to the template so it can render inline feedback
                # next to the password field (better UX and less noisy flashes).
                return render_template('register.html', **form_values, missing_passwords=missing)

            # Validate age (must be 13 or older)
            if not validate_age(date_of_birth):
                flash('You must be at least 13 years old to register.', 'danger')
                return render_template('register.html', **form_values)

            # Validate username format (3-30 characters, letters, numbers, underscores only)
            import re
            if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
                flash('Username must be 3-30 characters long and contain only letters, numbers, and underscores.', 'danger')
                return render_template('register.html', **form_values)

            # Validate date format (YYYY-MM-DD)
            try:
                if date_of_birth:
                    datetime.strptime(date_of_birth, '%Y-%m-%d')
            except ValueError:
                flash('Please enter a valid date of birth (YYYY-MM-DD).', 'danger')
                return render_template('register.html')

            # Create full name
            name = f"{first_name} {last_name}"

            password_hash = generate_password_hash(password)
            created_at = datetime.now().isoformat()

            conn = get_db()
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO users
                            (name, username, email, password_hash, created_at, date_of_birth, gender, contact_number, address)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (name, username, email, password_hash, created_at, date_of_birth, gender, contact_number, address))
                conn.commit()
                # Do not send verification email; mark user active immediately
                flash('Registration successful! You can now login.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError as e:
                if 'username' in str(e):
                    flash('Username already taken. Please choose a different username.', 'danger')
                elif 'email' in str(e):
                    flash('Email already registered.', 'danger')
                else:
                    flash('An error occurred during registration.', 'danger')
            finally:
                conn.close()
            return render_template('register.html', **form_values)
        # GET or initial render
        return render_template('register.html')

    # Email verification route removed: users are active immediately after registration.
    # Vaccine Schedule Management
    @app.route('/admin/vaccine-schedules')
    @admin_required
    def admin_vaccine_schedules():
        conn = get_db()
        c = conn.cursor()

        # Get all vaccine schedules ordered by vaccine name and dose number
        c.execute('''
            SELECT * FROM vaccine_schedules
            ORDER BY vaccine_name, dose_number
        ''')
        schedules = [dict(row) for row in c.fetchall()]

        conn.close()

        return render_template('admin_vaccine_schedules.html', schedules=schedules)

    @app.route('/admin/vaccine-schedule/add', methods=['GET', 'POST'])
    @admin_required
    def admin_add_vaccine_schedule():
        if request.method == 'POST':
            vaccine_name = request.form.get('vaccine_name')
            description = request.form.get('description')
            recommended_age = request.form.get('recommended_age')
            dose_number = int(request.form.get('dose_number', 1))
            is_booster = 1 if request.form.get('is_booster') else 0
            days_after_previous = request.form.get('days_after_previous_dose')
            
            conn = get_db()
            c = conn.cursor()
            
            try:
                c.execute('''
                    INSERT INTO vaccine_schedules 
                    (vaccine_name, description, recommended_age, dose_number, is_booster, days_after_previous_dose)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (vaccine_name, description, recommended_age, dose_number, is_booster, days_after_previous))
                
                conn.commit()
                flash('Vaccine schedule added successfully!', 'success')
                return redirect(url_for('admin_vaccine_schedules'))
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                flash('Error adding vaccine schedule. Please try again.', 'danger')
                
        return render_template('admin_vaccine_schedule_form.html', schedule=None)
    
    @app.route('/admin/vaccine-schedule/edit/<int:schedule_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_vaccine_schedule(schedule_id):
        conn = get_db()
        c = conn.cursor()
        
        if request.method == 'POST':
            vaccine_name = request.form.get('vaccine_name')
            description = request.form.get('description')
            recommended_age = request.form.get('recommended_age')
            dose_number = int(request.form.get('dose_number', 1))
            is_booster = 1 if request.form.get('is_booster') else 0
            days_after_previous = request.form.get('days_after_previous_dose')
            
            try:
                c.execute('''
                    UPDATE vaccine_schedules 
                    SET vaccine_name = ?, description = ?, recommended_age = ?, 
                        dose_number = ?, is_booster = ?, days_after_previous_dose = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (vaccine_name, description, recommended_age, dose_number, 
                     is_booster, days_after_previous, schedule_id))
                
                conn.commit()
                flash('Vaccine schedule updated successfully!', 'success')
                return redirect(url_for('admin_vaccine_schedules'))
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                flash('Error updating vaccine schedule. Please try again.', 'danger')
        
        # Get the schedule to edit
        c.execute('SELECT * FROM vaccine_schedules WHERE id = ?', (schedule_id,))
        schedule = c.fetchone()
        
        if not schedule:
            flash('Vaccine schedule not found.', 'danger')
            return redirect(url_for('admin_vaccine_schedules'))
            
        return render_template('admin_vaccine_schedule_form.html', schedule=dict(schedule))
    
    @app.route('/admin/vaccine-schedule/delete/<int:schedule_id>', methods=['POST'])
    @admin_required
    def admin_delete_vaccine_schedule(schedule_id):
        conn = get_db()
        c = conn.cursor()
        
        try:
            c.execute('DELETE FROM vaccine_schedules WHERE id = ?', (schedule_id,))
            conn.commit()
            flash('Vaccine schedule deleted successfully!', 'success')
        except sqlite3.Error as e:
            conn.rollback()
            flash('Error deleting vaccine schedule. Please try again.', 'danger')
        
        return redirect(url_for('admin_vaccine_schedules'))
    
    # Admin: Add new vaccine record
    @app.route('/admin/users/<int:user_id>/vaccine-records/add', methods=['GET', 'POST'])
    @admin_required
    def admin_add_vaccine_record(user_id):
        conn = get_db()
        c = conn.cursor()
        
        # Get user info
        c.execute('SELECT id, name FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        # Get available vaccines from vaccine_schedules
        c.execute('''
            SELECT * FROM vaccine_schedules 
            ORDER BY vaccine_name, dose_number
        ''')
        available_vaccines = [dict(row) for row in c.fetchall()]
        
        if not available_vaccines:
            flash('No vaccine schedules found. Please add vaccine schedules first.', 'warning')
            return redirect(url_for('admin_vaccine_schedules'))
        
        if request.method == 'POST':
            try:
                # Get form data
                vaccine_schedule_id = request.form.get('vaccine_schedule_id')
                administered_date = request.form.get('administered_date')
                administered_by = request.form.get('administered_by')
                location = request.form.get('location')
                notes = request.form.get('notes', '')
                
                # Validate required fields
                if not all([vaccine_schedule_id, administered_date, administered_by, location]):
                    flash('Please fill in all required fields.', 'danger')
                    return render_template(
                        'admin_add_vaccine_record.html',
                        user_id=user_id,
                        available_vaccines=available_vaccines,
                        today=datetime.now().strftime('%Y-%m-%d')
                    )
                
                # Check if this vaccine schedule exists for this user
                c.execute('''
                    SELECT id FROM user_vaccine_records 
                    WHERE user_id = ? AND vaccine_schedule_id = ?
                ''', (user_id, vaccine_schedule_id))
                
                if c.fetchone():
                    flash('This vaccine has already been recorded for this user.', 'warning')
                    return redirect(url_for('admin_view_user', user_id=user_id))
                
                # Insert the new record
                c.execute('''
                    INSERT INTO user_vaccine_records 
                    (user_id, vaccine_schedule_id, administered_date, 
                     administered_by, location, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    vaccine_schedule_id,
                    administered_date,
                    administered_by,
                    location,
                    notes,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                flash('Vaccine record added successfully!', 'success')
                return redirect(url_for('admin_view_user', user_id=user_id))
                
            except sqlite3.Error as e:
                conn.rollback()
                app.logger.error(f"Error adding vaccine record: {str(e)}")
                flash('An error occurred while adding the vaccine record.', 'danger')
        
        # For GET request or if there was an error
        return render_template(
            'admin_add_vaccine_record.html',
            user_id=user_id,
            available_vaccines=available_vaccines,
            today=datetime.now().strftime('%Y-%m-%d')
        )
    
    # Admin: Edit vaccine record
    @app.route('/admin/vaccine-records/<int:record_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_vaccine_record(record_id):
        conn = get_db()
        c = conn.cursor()
        
        # Get the vaccine record with user and vaccine details
        c.execute('''
            SELECT 
                vr.*, 
                u.id as user_id,
                u.name as user_name,
                vs.vaccine_name,
                vs.dose_number,
                vs.recommended_age
            FROM user_vaccine_records vr
            JOIN users u ON vr.user_id = u.id
            JOIN vaccine_schedules vs ON vr.vaccine_schedule_id = vs.id
            WHERE vr.id = ?
        ''', (record_id,))
        
        record = c.fetchone()
        
        if not record:
            flash('Vaccine record not found.', 'danger')
            return redirect(url_for('admin_dashboard'))
            
        record = dict(record)
        
        if request.method == 'POST':
            try:
                # Get form data
                administered_date = request.form.get('administered_date')
                administered_by = request.form.get('administered_by')
                location = request.form.get('location')
                notes = request.form.get('notes', '')
                
                # Validate required fields
                if not all([administered_date, administered_by, location]):
                    flash('Please fill in all required fields.', 'danger')
                    return render_template('admin_edit_vaccine_record.html', record=record)
                
                # Update the record
                c.execute('''
                    UPDATE user_vaccine_records
                    SET administered_date = ?,
                        administered_by = ?,
                        location = ?,
                        notes = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (
                    administered_date,
                    administered_by,
                    location,
                    notes,
                    datetime.now().isoformat(),
                    record_id
                ))
                
                conn.commit()
                flash('Vaccine record updated successfully!', 'success')
                return redirect(url_for('admin_view_user', user_id=record['user_id']))
                
            except sqlite3.Error as e:
                conn.rollback()
                app.logger.error(f"Error updating vaccine record: {str(e)}")
                flash('An error occurred while updating the vaccine record.', 'danger')
        
        # Get available vaccines for the dropdown
        c.execute('''
            SELECT * FROM vaccine_schedules 
            ORDER BY vaccine_name, dose_number
        ''')
        available_vaccines = [dict(row) for row in c.fetchall()]
        
        # For GET request or if there was an error
        return render_template(
            'admin_edit_vaccine_record.html', 
            record=record,
            user_id=record['user_id'],
            available_vaccines=available_vaccines
        )
    
    # Admin: Delete vaccine record
    @app.route('/admin/vaccine-records/<int:record_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_vaccine_record(record_id):
        conn = get_db()
        c = conn.cursor()
        
        try:
            # Get user_id for redirect
            c.execute('SELECT user_id FROM user_vaccine_records WHERE id = ?', (record_id,))
            record = c.fetchone()
            
            if not record:
                flash('Vaccine record not found.', 'danger')
                return redirect(url_for('admin_dashboard'))
            
            user_id = record[0]
            
            # Delete the record
            c.execute('DELETE FROM user_vaccine_records WHERE id = ?', (record_id,))
            conn.commit()
            
            flash('Vaccine record deleted successfully!', 'success')
            return redirect(url_for('admin_view_user', user_id=user_id))
            
        except sqlite3.Error as e:
            conn.rollback()
            app.logger.error(f"Error deleting vaccine record: {str(e)}")
            flash('An error occurred while deleting the vaccine record.', 'danger')
            return redirect(url_for('admin_dashboard'))
    
    # Admin: Generate PDF for any user
    @app.route('/admin/user/<int:user_id>/vaccine-record')
    @admin_required
    def admin_generate_vaccine_record(user_id):
        conn = get_db()
        c = conn.cursor()
        
        # Get user info
        c.execute('SELECT id, name, email, date_of_birth FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        # Get user's vaccine records with vaccine names
        c.execute('''
            SELECT 
                vr.*,
                vs.vaccine_name,
                vs.dose_number,
                vs.recommended_age
            FROM user_vaccine_records vr
            JOIN vaccine_schedules vs ON vr.vaccine_schedule_id = vs.id
            WHERE vr.user_id = ?
            ORDER BY vr.administered_date DESC
        ''', (user_id,))
        
        records = [dict(row) for row in c.fetchall()]
        
        # Generate PDF
        user_data = dict(user)
        pdf_buffer = generate_vaccine_record_pdf(
            user_data=user_data,
            vaccine_records=records,
            logo_path=os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
        )
        
        # Create response with PDF
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=vaccine_record_{user_id}_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return response
    
    # User Homepage
    @app.route('/user/home')
    @login_required
    def user_home():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        conn = get_db()
        c = conn.cursor()
        
        # Get user info
        c.execute('''
            SELECT id, name, email, created_at, last_login 
            FROM users WHERE id = ?
        ''', (session['user_id'],))
        user = c.fetchone()
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))
        
        return render_template('user_home.html', 
                             current_user=dict(user))

    # User Dashboard
    @app.route('/user/dashboard')
    @login_required
    def user_dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        conn = get_db()
        c = conn.cursor()
        
        # Get user info
        c.execute('''
            SELECT id, name, email, created_at, last_login 
            FROM users WHERE id = ?
        ''', (session['user_id'],))
        user = c.fetchone()
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))
        
        # Get user's vaccine records with vaccine names
        c.execute('''
            SELECT 
                vr.*,
                vs.vaccine_name,
                vs.dose_number,
                vs.recommended_age
            FROM user_vaccine_records vr
            JOIN vaccine_schedules vs ON vr.vaccine_schedule_id = vs.id
            WHERE vr.user_id = ?
            ORDER BY vr.administered_date DESC
        ''', (session['user_id'],))
        
        records = [dict(row) for row in c.fetchall()]
        
        return render_template('user_dashboard.html', 
                             current_user=dict(user),
                             vaccine_records=records)
    
    # User: Generate own PDF record
    @app.route('/user/vaccine-record')
    @login_required
    def user_vaccine_record():
        if 'user_id' not in session:
            return redirect(url_for('login'))
            
        conn = get_db()
        c = conn.cursor()
        
        # Get user info
        c.execute('SELECT id, name, email, date_of_birth FROM users WHERE id = ?', (session['user_id'],))
        user = c.fetchone()
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('dashboard'))
        
        # Get user's vaccine records with vaccine names
        c.execute('''
            SELECT 
                vr.*,
                vs.vaccine_name,
                vs.dose_number,
                vs.recommended_age
            FROM user_vaccine_records vr
            JOIN vaccine_schedules vs ON vr.vaccine_schedule_id = vs.id
            WHERE vr.user_id = ?
            ORDER BY vr.administered_date DESC
        ''', (session['user_id'],))
        
        records = [dict(row) for row in c.fetchall()]
        
        # Generate PDF
        user_data = dict(user)
        pdf_buffer = generate_vaccine_record_pdf(
            user_data=user_data,
            vaccine_records=records,
            logo_path=os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
        )
        
        # Create response with PDF
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=my_vaccine_record_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return response

    @app.route('/edit-profile', methods=['GET', 'POST'])
    @login_required
    def edit_profile():
        print("DEBUG: Edit profile route accessed")
        get_db = app.get_db
        mail = app.mail
        serializer = app.serializer
        user_id = session.get('user_id')
        if not user_id:
            print("DEBUG: No user_id in session, redirecting to login")
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        print(f"DEBUG: User ID from session: {user_id}")
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            contact_number = request.form.get('contact_number')
            date_of_birth = request.form.get('date_of_birth')
            gender = request.form.get('gender')

            query_parts = []
            params = []

            if name:
                query_parts.append('name = ?')
                params.append(name)
            if email:
                query_parts.append('email = ?')
                params.append(email)
            if contact_number:
                query_parts.append('contact_number = ?')
                params.append(contact_number)
            if date_of_birth:
                query_parts.append('date_of_birth = ?')
                params.append(date_of_birth)
            if gender:
                query_parts.append('gender = ?')
                params.append(gender)
            if password:
                missing = get_missing_password_requirements(password)
                if missing:
                    for req in missing:
                        flash(f"Password must contain {req}.", 'danger')
                    conn.close()
                    return render_template('edit_profile.html')
                password_hash = generate_password_hash(password)
                query_parts.append('password_hash = ?')
                params.append(password_hash)

            if not query_parts:
                flash('No fields to update.', 'info')
                return redirect(url_for('edit_profile'))

            query = f"UPDATE users SET {', '.join(query_parts)} WHERE id = ?"
            params.append(user_id)

            try:
                c.execute(query, tuple(params))
                conn.commit()
                flash('Profile updated successfully!', 'success')
                # Update session with new name and email
                if name:
                    session['user_name'] = name
                if email:
                    session['user_email'] = email
            except sqlite3.IntegrityError:
                conn.rollback()
                flash('Email address is already in use.', 'danger')
            except Exception as e:
                conn.rollback()
                flash('An error occurred while updating your profile.', 'danger')
            finally:
                conn.close()
            
            return redirect(url_for('edit_profile'))

        # For GET request, fetch current user data
        c.execute('SELECT id, name, email, address, contact_number, date_of_birth, gender FROM users WHERE id = ?', (user_id,))
        user_row = c.fetchone()
        user_data = dict(user_row) if user_row else {}

        # Compute age from date_of_birth if available
        dob_val = user_data.get('date_of_birth')
        if dob_val:
            try:
                from datetime import datetime, date
                dob_date = datetime.strptime(dob_val, '%Y-%m-%d').date()
                today = date.today()
                age_calc = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                user_data['age'] = age_calc
            except Exception:
                user_data['age'] = None
        else:
            user_data['age'] = None

        conn.close()

        # Determine whether we're rendering the edit form or a read-only view.
        edit_mode = True if request.args.get('edit') in ('1', 'true', 'yes') else False

        return render_template('edit_profile.html', current_user=user_data, edit_mode=edit_mode)

    @app.route('/update-sms-settings', methods=['POST'])
    @login_required
    def update_sms_settings():
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))

        # Get SMS settings from form
        phone_number = request.form.get('phone_number', '').strip()
        appointment_reminders = 1 if request.form.get('appointment_reminders') else 0
        appointment_confirmations = 1 if request.form.get('appointment_confirmations') else 0
        vaccine_reminders = 1 if request.form.get('vaccine_reminders') else 0
        general_notifications = 1 if request.form.get('general_notifications') else 0
        marketing_messages = 1 if request.form.get('marketing_messages') else 0

        # Validate phone number if provided
        if phone_number:
            from utils.sms_service import SMSService
            sms_service = SMSService(current_app)
            if not sms_service.validate_phone_number(phone_number):
                flash('Please enter a valid Philippine mobile number (09XXXXXXXXX).', 'danger')
                return redirect(url_for('edit_profile'))

        # Update SMS settings
        settings_data = {
            'phone_number': phone_number,
            'appointment_reminders': appointment_reminders,
            'appointment_confirmations': appointment_confirmations,
            'vaccine_reminders': vaccine_reminders,
            'general_notifications': general_notifications,
            'marketing_messages': marketing_messages
        }

        try:
            conn = current_app.get_db()
            c = conn.cursor()

            # Check if settings exist for user
            c.execute('SELECT id FROM sms_settings WHERE user_id = ?', (user_id,))
            existing = c.fetchone()

            if existing:
                # Update existing settings
                c.execute('''
                    UPDATE sms_settings
                    SET phone_number = ?, appointment_reminders = ?, appointment_confirmations = ?,
                        vaccine_reminders = ?, general_notifications = ?, marketing_messages = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (phone_number, appointment_reminders, appointment_confirmations,
                     vaccine_reminders, general_notifications, marketing_messages, user_id))
            else:
                # Create new settings
                c.execute('''
                    INSERT INTO sms_settings (user_id, phone_number, appointment_reminders,
                                            appointment_confirmations, vaccine_reminders,
                                            general_notifications, marketing_messages)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, phone_number, appointment_reminders, appointment_confirmations,
                     vaccine_reminders, general_notifications, marketing_messages))

            conn.commit()
            flash('SMS settings updated successfully!', 'success')

        except Exception as e:
            flash('Error updating SMS settings. Please try again.', 'danger')
            current_app.logger.error(f'Error updating SMS settings for user {user_id}: {str(e)}')

        finally:
            if 'conn' in locals():
                conn.close()

        return redirect(url_for('edit_profile'))

    @app.route('/my-bookings')
    @login_required
    def my_bookings():
        print("DEBUG: My bookings route accessed")
        get_db = app.get_db
        mail = app.mail
        serializer = app.serializer
        user_id = session.get('user_id')
        if not user_id:
            print("DEBUG: No user_id in session, redirecting to login")
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        print(f"DEBUG: User ID from session: {user_id}")
        conn = get_db()
        c = conn.cursor()

        # Fetch current user data for the sidebar
        c.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,))
        current_user = c.fetchone()

        # Fetch bookings with date filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = 'SELECT id, service, appointment_date, status, price FROM appointments WHERE user_id = ?'
        params = [user_id]

        if start_date and end_date:
            query += ' AND appointment_date BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        
        query += ' ORDER BY appointment_date DESC'

        c.execute(query, tuple(params))
        bookings = c.fetchall()
        conn.close()

        return render_template('my_bookings.html', current_user=current_user, bookings=bookings)

    @app.route('/my-bookings/view/<int:booking_id>')
    @login_required
    def view_booking(booking_id):
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view bookings.', 'danger')
            return redirect(url_for('login'))

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM appointments WHERE id = ? AND user_id = ?', (booking_id, user_id))
        booking = c.fetchone()
        conn.close()

        if not booking:
            flash('Booking not found.', 'danger')
            return redirect(url_for('my_bookings'))

        # Convert row to dict for template convenience
        booking_data = dict(booking)
        return render_template('booking_details.html', booking=booking_data)

    @app.route('/my-bookings/api/<int:booking_id>')
    @login_required
    def booking_api(booking_id):
        """Return booking details as JSON for the current user."""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required.'}), 401

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM appointments WHERE id = ? AND user_id = ?', (booking_id, user_id))
        row = c.fetchone()
        conn.close()

        if not row:
            return jsonify({'success': False, 'message': 'Booking not found.'}), 404

        try:
            booking = dict(row)
        except Exception:
            # Fallback: build dict from cursor description
            booking = {k: row[idx] for idx, k in enumerate([d[0] for d in c.description])}

        # Ensure types are JSON serializable (sqlite returns numbers/strings)
        return jsonify({'success': True, 'booking': booking})

    @app.route('/my-bookings/cancel/<int:booking_id>', methods=['POST'])
    @login_required
    def cancel_my_booking(booking_id):
        """Allow a logged-in user to cancel their own booking via AJAX."""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Authentication required.'}), 401

        conn = get_db()
        c = conn.cursor()
        # Ensure the booking exists and belongs to the current user
        c.execute('SELECT id, status, user_id, patient_phone, appointment_date, appointment_time FROM appointments WHERE id = ? AND user_id = ?', (booking_id, user_id))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'message': 'Booking not found or access denied.'}), 404

        current_status = row['status'] if isinstance(row, dict) else row[1]
        # Prevent cancelling completed or already-cancelled appointments
        if current_status in ('completed', 'cancelled'):
            conn.close()
            return jsonify({'success': False, 'message': 'This appointment cannot be cancelled.'}), 400

        try:
            # Update status to cancelled
            c.execute('UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?', ('cancelled', datetime.now().isoformat(), booking_id))
            conn.commit()

            # Optionally send SMS notification for cancellation if patient_phone exists
            try:
                patient_phone = row['patient_phone'] if isinstance(row, dict) else row[3]
                if patient_phone:
                    try:
                        from utils.sms import send_message
                        msg = f"Your appointment on {row['appointment_date'] if isinstance(row, dict) else row[4]} at {row['appointment_time'] if isinstance(row, dict) else row[5]} has been cancelled."
                        send_message(patient_phone, msg)
                    except Exception:
                        # don't fail the cancellation if SMS sending fails
                        pass
            except Exception:
                pass

            conn.close()
            return jsonify({'success': True, 'message': 'Appointment cancelled successfully.'})
        except Exception as e:
            conn.rollback()
            conn.close()
            current_app.logger.error(f'Error cancelling appointment {booking_id} for user {user_id}: {e}')
            return jsonify({'success': False, 'message': 'Failed to cancel appointment.'}), 500
    
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        conn = get_db()
        c = conn.cursor()

        # Get user statistics
        c.execute('SELECT COUNT(*) FROM users')
        user_count = c.fetchone()[0] or 0

        # Get active users today
        active_today = 0
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            c.execute('''
                SELECT COUNT(DISTINCT user_id)
                FROM user_activity
                WHERE date(activity_time) = ?
            ''', (today,))
            result = c.fetchone()
            active_today = result[0] if result and result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table might not exist yet or other DB error
            active_today = 0

        # Verification concept deprecated: no pending verifications
        pending_verifications = 0

        # Recent users (is_verified no longer shown)
        c.execute('SELECT id, name, email, created_at FROM users ORDER BY created_at DESC LIMIT 5')
        recent_users = [dict(row) for row in c.fetchall()]

        # Get appointment statistics for stat cards
        c.execute('SELECT COUNT(*) FROM appointments')
        total_appointments = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM appointments WHERE status = 'confirmed'")
        approved_appointments = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM appointments WHERE status = 'pending'")
        pending_appointments = c.fetchone()[0] or 0

        # Get recent appointments for the table
        c.execute('''
            SELECT a.*, u.name as user_name
            FROM appointments a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
            LIMIT 10
        ''')
        recent_appointments = [dict(row) for row in c.fetchall()]

        # Chart data - Initialize chart data dictionary
        chart_data = {}

        # Chart data - Appointment status distribution
        c.execute('''
            SELECT status, COUNT(*) as count
            FROM appointments
            GROUP BY status
            ORDER BY count DESC
        ''')
        status_data = c.fetchall()
        chart_data['appointment_status_labels'] = [row[0] for row in status_data]
        chart_data['appointment_status_values'] = [row[1] for row in status_data]

        # Weekly appointment trends (last 7 days)
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        c.execute('''
            SELECT DATE(appointment_date) as date, COUNT(*) as count
            FROM appointments
            WHERE appointment_date >= ?
            GROUP BY DATE(appointment_date)
            ORDER BY date
        ''', (seven_days_ago,))
        weekly_data = c.fetchall()
        chart_data['weekly_appointment_labels'] = [row[0] for row in weekly_data]
        chart_data['weekly_appointment_values'] = [row[1] for row in weekly_data]

        # Get user activity log
        c.execute('''
            SELECT ua.activity_type, ua.activity_time, ua.ip_address, ua.user_agent, u.name, u.email
            FROM user_activity ua
            JOIN users u ON ua.user_id = u.id
            ORDER BY ua.activity_time DESC
            LIMIT 10
        ''')
        recent_activities = [dict(row) for row in c.fetchall()]

        # Chart data - User registration trends (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        c.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (thirty_days_ago,))
        registration_data = c.fetchall()
        chart_data['registration_labels'] = [row[0] for row in registration_data]
        chart_data['registration_values'] = [row[1] for row in registration_data]

        # Service popularity
        c.execute('''
            SELECT service, COUNT(*) as count
            FROM appointments
            GROUP BY service
            ORDER BY count DESC
        ''')
        service_data = c.fetchall()
        chart_data['service_labels'] = [row[0] for row in service_data]
        chart_data['service_values'] = [row[1] for row in service_data]

        # Appointment trends (last 30 days)
        c.execute('''
            SELECT DATE(appointment_date) as date, COUNT(*) as count
            FROM appointments
            WHERE appointment_date >= ?
            GROUP BY DATE(appointment_date)
            ORDER BY date
        ''', (thirty_days_ago,))
        appointment_data = c.fetchall()
        chart_data['appointment_labels'] = [row[0] for row in appointment_data]
        chart_data['appointment_values'] = [row[1] for row in appointment_data]

        # Vaccine administration trends
        c.execute('''
            SELECT vs.vaccine_name, COUNT(*) as count
            FROM user_vaccine_records vr
            JOIN vaccine_schedules vs ON vr.vaccine_schedule_id = vs.id
            GROUP BY vs.vaccine_name
            ORDER BY count DESC
        ''')
        vaccine_data = c.fetchall()
        chart_data['vaccine_labels'] = [row[0] for row in vaccine_data]
        chart_data['vaccine_values'] = [row[1] for row in vaccine_data]

        # Weekly sales (last 7 days) - sum of appointment prices per day
        try:
            # Build a map of date -> total sales
            seven_days_ago_sales = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')
            c.execute('''
                SELECT DATE(appointment_date) as date, COALESCE(SUM(price), 0) as total
                FROM appointments
                WHERE appointment_date >= ?
                GROUP BY DATE(appointment_date)
                ORDER BY date
            ''', (seven_days_ago_sales,))
            sales_rows = c.fetchall()
            sales_map = {row[0]: float(row[1] or 0) for row in sales_rows}

            # Ensure we produce a label for each of the last 7 days (oldest -> newest)
            weekly_labels = []
            weekly_values = []
            for i in range(6, -1, -1):
                d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                weekly_labels.append(d)
                weekly_values.append(sales_map.get(d, 0.0))

            chart_data['weekly_sales_labels'] = weekly_labels
            chart_data['weekly_sales_values'] = weekly_values
        except Exception:
            # If anything goes wrong (missing table/column), fall back to empty arrays
            chart_data['weekly_sales_labels'] = []
            chart_data['weekly_sales_values'] = []

        # Consolidate client-side dashboard payload to avoid multiple scattered template injections
        dashboard_payload = {
            'chart_data': chart_data,
            'recent_appointments': recent_appointments
        }

        conn.close()

        return render_template('admin_dashboard.html',
                             user_count=user_count,
                             active_today=active_today,
                             pending_verifications=pending_verifications,
                             recent_users=recent_users,
                             recent_activities=recent_activities,
                             chart_data=chart_data,
                             total_appointments=total_appointments,
                             approved_appointments=approved_appointments,
                             pending_appointments=pending_appointments,
                             recent_appointments=recent_appointments,
                             dashboard_payload=dashboard_payload)
    
    @app.route('/admin/users')
    @admin_required
    def admin_users():
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        conn = get_db()
        c = conn.cursor()
        
        # Get total count for pagination
        if search:
            c.execute('''
                SELECT COUNT(*) FROM users 
                WHERE name LIKE ? OR email LIKE ?
            ''', (f'%{search}%', f'%{search}%'))
        else:
            c.execute('SELECT COUNT(*) FROM users')
        
        total_users = c.fetchone()[0] or 0
        
        # Get paginated users
        offset = (page - 1) * per_page
        if search:
            c.execute('''
                SELECT id, name, email, created_at, contact_number
                FROM users
                WHERE name LIKE ? OR email LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (f'%{search}%', f'%{search}%', per_page, offset))
        else:
            c.execute('''
                SELECT id, name, email, created_at, contact_number
                FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
        
        users = [dict(row) for row in c.fetchall()]
        
        # Get appointment data for each user
        for user in users:
            # Get recent appointment
            c.execute('''
                SELECT appointment_date, appointment_time, service
                FROM appointments
                WHERE user_id = ?
                ORDER BY appointment_date DESC, appointment_time DESC
                LIMIT 1
            ''', (user['id'],))
            appointment = c.fetchone()
            
            # Get appointment count
            c.execute('SELECT COUNT(*) FROM appointments WHERE user_id = ?', (user['id'],))
            count_result = c.fetchone()
            
            if appointment and count_result:
                user['recent_appointment'] = f"{appointment['appointment_date']} | {appointment['appointment_time']}"
                user['appointment_count'] = count_result[0]
            else:
                user['recent_appointment'] = 'No appointments'
                user['appointment_count'] = 0
        
        conn.close()
        
        return render_template('admin_users.html', users=users, search=search, page=page, per_page=per_page, total_users=total_users)
    @app.route('/admin/users/add', methods=['GET', 'POST'])
    @admin_required
    def admin_add_user():
        if request.method == 'POST':
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            date_of_birth = request.form.get('date_of_birth')
            gender = request.form.get('gender')
            contact_number = request.form.get('contact_number')
            address = request.form.get('address')
            # Verification flag deprecated; mark admin-created users as active immediately
            is_verified = 1

            # Validate required fields
            if not all([first_name, last_name, username, email, password, confirm_password, date_of_birth, gender, contact_number, address]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin_add_user.html')

            # Validate password strength
            missing = get_missing_password_requirements(password)
            if missing:
                for req in missing:
                    flash(f"Password must contain {req}.", 'danger')
                return render_template('admin_add_user.html')

            # Check if passwords match
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('admin_add_user.html')

            # Validate age (must be 13 or older)
            if not validate_age(date_of_birth):
                flash('User must be at least 13 years old.', 'danger')
                return render_template('admin_add_user.html')

            # Validate username format (3-30 characters, letters, numbers, underscores only)
            if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
                flash('Username must be 3-30 characters long and contain only letters, numbers, and underscores.', 'danger')
                return render_template('admin_add_user.html')

            # Validate date format (YYYY-MM-DD)
            try:
                datetime.strptime(date_of_birth, '%Y-%m-%d')
            except ValueError:
                flash('Please enter a valid date of birth (YYYY-MM-DD).', 'danger')
                return render_template('admin_add_user.html')

            # Check if username or email already exists
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if c.fetchone():
                flash('Username or email already exists.', 'danger')
                conn.close()
                return render_template('admin_add_user.html')

            # Create full name
            name = f"{first_name} {last_name}"

            # Create user
            password_hash = generate_password_hash(password)
            created_at = datetime.now().isoformat()

            try:
                c.execute('''
                    INSERT INTO users
                    (name, username, email, password_hash, is_verified, created_at, date_of_birth, gender, contact_number, address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, username, email, password_hash, is_verified, created_at, date_of_birth, gender, contact_number, address))

                conn.commit()
                flash('User added successfully!', 'success')
                return redirect(url_for('admin_users'))

            except sqlite3.IntegrityError:
                conn.rollback()
                flash('An error occurred while adding the user.', 'danger')
            finally:
                conn.close()

        return render_template('admin_add_user.html')

    @app.route('/admin/users/export')
    @admin_required
    def admin_users_export():
        # Apply same search filter as admin_users()
        search = request.args.get('search', '')

        conn = get_db()
        c = conn.cursor()

        # Determine available columns (last_login may not exist)
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]

        select_columns = ['id', 'name', 'email', 'created_at']
        if 'last_login' in columns:
            select_columns.append('last_login')

        base_query = f"SELECT {', '.join(select_columns)} FROM users"
        params = []
        if search:
            base_query += " WHERE name LIKE ? OR email LIKE ?"
            params = [f'%{search}%', f'%{search}%']
        base_query += " ORDER BY created_at DESC"

        c.execute(base_query, params)
        rows = [dict(row) for row in c.fetchall()]
        conn.close()

        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)
        # Header
        header = [
            'ID', 'Name', 'Email', 'Created At'
        ] + (['Last Login'] if 'last_login' in select_columns else [])
        writer.writerow(header)
        # Rows
        for r in rows:
            row = [
                r.get('id'),
                r.get('name'),
                r.get('email'),
                r.get('created_at')
            ]
            if 'last_login' in select_columns:
                row.append(r.get('last_login'))
            writer.writerow(row)

        csv_data = output.getvalue()
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=customers_export.csv'
        return response
    
    @app.route('/admin/users/<int:user_id>')
    @admin_required
    def admin_view_user(user_id):
        conn = get_db()
        c = conn.cursor()
        
        # First, check if last_login column exists
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        
        # Build the query based on available columns
        select_columns = ['id', 'name', 'email', 'is_verified', 'created_at']
        # Optional columns we want to surface in admin view
        optional_columns = ['last_login', 'date_of_birth', 'gender', 'contact_number', 'address']
        for col in optional_columns:
            if col in columns:
                select_columns.append(col)
            
        query = f"""
            SELECT {', '.join(select_columns)}
            FROM users 
            WHERE id = ?
        """
        
        c.execute(query, (user_id,))
        user = c.fetchone()
        
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))
            
        # Convert to dict and add last_login as None if not present
        user_dict = dict(user)
        # Ensure optional keys exist with sensible defaults
        for key in ['last_login', 'date_of_birth', 'gender', 'contact_number', 'address']:
            if key not in user_dict:
                user_dict[key] = None

        # Compute age from date_of_birth for display (if available)
        if user_dict.get('date_of_birth'):
            try:
                dob = datetime.strptime(user_dict['date_of_birth'], '%Y-%m-%d')
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                user_dict['age'] = age
            except Exception:
                user_dict['age'] = None
        else:
            user_dict['age'] = None
        
        # Get user's recent activity
        c.execute('''
            SELECT activity_type, activity_time, ip_address, user_agent 
            FROM user_activity 
            WHERE user_id = ? 
            ORDER BY activity_time DESC 
            LIMIT 10
        ''', (user_id,))
        activities = c.fetchall()
        
        # Get user's vaccine records with vaccine names
        c.execute('''
            SELECT 
                vr.id,
                vr.administered_date,
                vr.administered_by,
                vr.location,
                vr.notes,
                vs.vaccine_name,
                vs.dose_number,
                vs.recommended_age
            FROM user_vaccine_records vr
            JOIN vaccine_schedules vs ON vr.vaccine_schedule_id = vs.id
            WHERE vr.user_id = ?
            ORDER BY vs.vaccine_name, vs.dose_number
        ''', (user_id,))
        
        vaccine_records = [dict(row) for row in c.fetchall()]
        conn.close()
        
        # Add vaccine records to user_dict for the template
        user_dict['vaccine_records'] = vaccine_records
        
        return render_template('admin_user_view.html', user=user_dict, activities=activities)
    
    # Admin is not allowed to edit user information via the admin UI per updated policy.
    # The edit route was removed to prevent administrators from manipulating user profiles.
            
    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_user(user_id):
        if 'confirm' in request.form:
            conn = get_db()
            c = conn.cursor()
            
            try:
                # Get user name for confirmation message
                c.execute('SELECT name FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                
                if not user:
                    flash('User not found', 'danger')
                    return redirect(url_for('admin_users'))
                
                user_name = user[0]
                
                # Delete related records first (due to foreign key constraints)
                c.execute('DELETE FROM user_vaccine_records WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM appointments WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM user_documents WHERE user_id = ?', (user_id,))
                
                # Delete user's activity logs
                c.execute('DELETE FROM user_activity WHERE user_id = ?', (user_id,))
                
                # Delete the user
                c.execute('DELETE FROM users WHERE id = ?', (user_id,))
                
                if c.rowcount > 0:
                    conn.commit()
                    flash(f'User "{user_name}" deleted successfully', 'success')
                else:
                    flash('User not found', 'danger')
                    
            except Exception as e:
                conn.rollback()
                flash('Error deleting user', 'danger')
                current_app.logger.error(f'Error deleting user {user_id}: {str(e)}')
                
            finally:
                conn.close()
        
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/archive', methods=['POST'])
    @admin_required
    def admin_archive_user(user_id):
        if 'confirm' in request.form:
            conn = get_db()
            c = conn.cursor()
            try:
                # Fetch user
                c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                if not user:
                    flash('User not found', 'danger')
                    return redirect(url_for('admin_users'))

                user_dict = dict(user)

                # Gather related records for snapshot
                c.execute('SELECT * FROM appointments WHERE user_id = ?', (user_id,))
                appointments = [dict(r) for r in c.fetchall()]

                c.execute('SELECT * FROM user_vaccine_records WHERE user_id = ?', (user_id,))
                vax = [dict(r) for r in c.fetchall()]

                c.execute('SELECT * FROM user_documents WHERE user_id = ?', (user_id,))
                docs = [dict(r) for r in c.fetchall()]

                c.execute('SELECT * FROM user_activity WHERE user_id = ?', (user_id,))
                activity = [dict(r) for r in c.fetchall()]

                snapshot = json.dumps({
                    'user': user_dict,
                    'appointments': appointments,
                    'vaccine_records': vax,
                    'documents': docs,
                    'activity': activity
                }, default=str)

                # Ensure archive table exists
                c.execute('''
                    CREATE TABLE IF NOT EXISTS archived_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_user_id INTEGER,
                        name TEXT,
                        username TEXT,
                        email TEXT,
                        password_hash TEXT,
                        is_verified INTEGER,
                        created_at TEXT,
                        date_of_birth TEXT,
                        gender TEXT,
                        contact_number TEXT,
                        address TEXT,
                        archived_at TEXT,
                        data TEXT
                    )
                ''')

                archived_at = datetime.now().isoformat()
                c.execute('''
                    INSERT INTO archived_users
                    (original_user_id, name, username, email, password_hash, is_verified, created_at, date_of_birth, gender, contact_number, address, archived_at, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_dict.get('id'),
                    user_dict.get('name'),
                    user_dict.get('username'),
                    user_dict.get('email'),
                    user_dict.get('password_hash'),
                    user_dict.get('is_verified'),
                    user_dict.get('created_at'),
                    user_dict.get('date_of_birth'),
                    user_dict.get('gender'),
                    user_dict.get('contact_number'),
                    user_dict.get('address'),
                    archived_at,
                    snapshot
                ))

                # Remove related records and user (mirror delete flow)
                c.execute('DELETE FROM user_vaccine_records WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM appointments WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM user_documents WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM user_activity WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM users WHERE id = ?', (user_id,))

                conn.commit()
                flash(f'User "{user_dict.get("name")}" archived successfully', 'success')
            except Exception as e:
                conn.rollback()
                flash('Error archiving user', 'danger')
                current_app.logger.error(f'Error archiving user {user_id}: {str(e)}')
            finally:
                conn.close()

        return redirect(url_for('admin_users'))

    @app.route('/admin/archived-users')
    @admin_required
    def admin_archived_users():
        conn = get_db()
        c = conn.cursor()
        # Check if archived_users table exists; if not, return empty list
        c.execute("PRAGMA table_info(archived_users)")
        cols = c.fetchall()
        rows = []
        if cols:
            # Support optional search by name, email or original_user_id
            search = request.args.get('search', '').strip()
            if search:
                # If search looks numeric, allow searching by original_user_id exact match
                params = []
                where_clauses = []
                where_clauses.append('(name LIKE ? OR email LIKE ? OR data LIKE ?)')
                params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
                if search.isdigit():
                    where_clauses.append('original_user_id = ?')
                    params.append(int(search))
                q = f"SELECT id, original_user_id, name, email, archived_at, data FROM archived_users WHERE {' OR '.join(where_clauses)} ORDER BY archived_at DESC"
                c.execute(q, params)
            else:
                c.execute("SELECT id, original_user_id, name, email, archived_at, data FROM archived_users ORDER BY archived_at DESC")
            rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return render_template('admin_archived_users.html', archived=rows, search=request.args.get('search', ''))

    @app.route('/admin/archived-users/<int:archived_id>/restore', methods=['POST'])
    @admin_required
    def admin_restore_archived_user(archived_id):
        conn = get_db()
        c = conn.cursor()
        try:
            # Ensure archive table exists
            c.execute("PRAGMA table_info(archived_users)")
            if not c.fetchall():
                flash('No archived users exist.', 'danger')
                return redirect(url_for('admin_archived_users'))

            c.execute('SELECT * FROM archived_users WHERE id = ?', (archived_id,))
            a = c.fetchone()
            if not a:
                flash('Archived user not found', 'danger')
                return redirect(url_for('admin_archived_users'))

            a_dict = dict(a)
            data = a_dict.get('data')
            # Basic restore: re-insert user row; related records are stored in snapshot but not restored automatically
            username = a_dict.get('username') or (a_dict.get('email') or '').split('@')[0]
            original_username = username
            i = 1
            while True:
                c.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, a_dict.get('email')))
                if not c.fetchone():
                    break
                username = f"{original_username}_{i}"
                i += 1

            c.execute('''
                INSERT INTO users (name, username, email, password_hash, is_verified, created_at, date_of_birth, gender, contact_number, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                a_dict.get('name'),
                username,
                a_dict.get('email'),
                a_dict.get('password_hash'),
                a_dict.get('is_verified') or 0,
                a_dict.get('created_at') or datetime.now().isoformat(),
                a_dict.get('date_of_birth'),
                a_dict.get('gender'),
                a_dict.get('contact_number'),
                a_dict.get('address')
            ))
            new_user_id = c.lastrowid

            # Remove archive entry after successful restore
            c.execute('DELETE FROM archived_users WHERE id = ?', (archived_id,))
            conn.commit()
            flash('Archived user restored successfully', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error restoring archived user', 'danger')
            current_app.logger.error(f'Error restoring archived user {archived_id}: {str(e)}')
        finally:
            conn.close()

        return redirect(url_for('admin_archived_users'))

    @app.route('/admin/archived-users/<int:archived_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_archived_user(archived_id):
        conn = get_db()
        c = conn.cursor()
        try:
            # Ensure archive table exists
            c.execute("PRAGMA table_info(archived_users)")
            if not c.fetchall():
                flash('No archived users exist.', 'danger')
                return redirect(url_for('admin_archived_users'))

            c.execute('SELECT id FROM archived_users WHERE id = ?', (archived_id,))
            if not c.fetchone():
                flash('Archived user not found', 'danger')
                return redirect(url_for('admin_archived_users'))
            c.execute('DELETE FROM archived_users WHERE id = ?', (archived_id,))
            conn.commit()
            flash('Archived record deleted permanently', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error deleting archived record', 'danger')
            current_app.logger.error(f'Error deleting archived user {archived_id}: {str(e)}')
        finally:
            conn.close()

        return redirect(url_for('admin_archived_users'))

    @app.route('/admin/appointments/<int:appointment_id>/archive', methods=['POST'])
    @admin_required
    def admin_archive_appointment(appointment_id):
        conn = get_db()
        c = conn.cursor()
        try:
            # Fetch appointment
            c.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,))
            appt = c.fetchone()
            if not appt:
                flash('Appointment not found', 'danger')
                return redirect(url_for('appointments.list_appointments'))

            appt_dict = dict(appt)

            # Ensure archive table exists
            c.execute('''
                CREATE TABLE IF NOT EXISTS archived_appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_appointment_id INTEGER,
                    patient_name TEXT,
                    user_id INTEGER,
                    service TEXT,
                    appointment_date TEXT,
                    appointment_time TEXT,
                    status TEXT,
                    archived_at TEXT,
                    data TEXT
                )
            ''')

            archived_at = datetime.now().isoformat()
            snapshot = json.dumps(appt_dict, default=str)
            c.execute('''
                INSERT INTO archived_appointments (original_appointment_id, patient_name, user_id, service, appointment_date, appointment_time, status, archived_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                appt_dict.get('id'),
                appt_dict.get('patient_name'),
                appt_dict.get('user_id'),
                appt_dict.get('service'),
                appt_dict.get('appointment_date'),
                appt_dict.get('appointment_time'),
                appt_dict.get('status'),
                archived_at,
                snapshot
            ))

            # Delete original appointment
            c.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
            conn.commit()
            flash('Appointment archived successfully', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error archiving appointment', 'danger')
            current_app.logger.error(f'Error archiving appointment {appointment_id}: {str(e)}')
        finally:
            conn.close()

        return redirect(url_for('appointments.list_appointments'))

    @app.route('/admin/archived-appointments')
    @admin_required
    def admin_archived_appointments():
        conn = get_db()
        c = conn.cursor()
        # Check if archived_appointments table exists; if not, return empty list
        c.execute("PRAGMA table_info(archived_appointments)")
        cols = c.fetchall()
        rows = []
        if cols:
            search = request.args.get('search', '').strip()
            if search:
                params = [f'%{search}%']
                q = "SELECT id, original_appointment_id, patient_name, appointment_date, appointment_time, status, archived_at, data FROM archived_appointments WHERE patient_name LIKE ? OR data LIKE ? ORDER BY archived_at DESC"
                params.append(f'%{search}%')
                c.execute(q, params)
            else:
                c.execute("SELECT id, original_appointment_id, patient_name, appointment_date, appointment_time, status, archived_at, data FROM archived_appointments ORDER BY archived_at DESC")
            rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return render_template('admin_archived_appointments.html', archived=rows, search=request.args.get('search', ''))

    @app.route('/admin/archived-appointments/<int:archived_id>/restore', methods=['POST'])
    @admin_required
    def admin_restore_archived_appointment(archived_id):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("PRAGMA table_info(archived_appointments)")
            if not c.fetchall():
                flash('No archived appointments exist.', 'danger')
                return redirect(url_for('admin_archived_appointments'))

            c.execute('SELECT * FROM archived_appointments WHERE id = ?', (archived_id,))
            a = c.fetchone()
            if not a:
                flash('Archived appointment not found', 'danger')
                return redirect(url_for('admin_archived_appointments'))

            a_dict = dict(a)
            data = a_dict.get('data')
            try:
                snapshot = json.loads(data) if data else {}
            except Exception:
                snapshot = {}

            # Get appointments table columns
            c.execute('PRAGMA table_info(appointments)')
            cols = [r[1] for r in c.fetchall()]
            insert_cols = [col for col in cols if col != 'id']
            values = []
            for col in insert_cols:
                values.append(snapshot.get(col))

            if not insert_cols:
                flash('Unable to restore appointment: target table schema not found', 'danger')
                return redirect(url_for('admin_archived_appointments'))

            placeholders = ','.join(['?'] * len(insert_cols))
            col_list = ','.join(insert_cols)
            c.execute(f'INSERT INTO appointments ({col_list}) VALUES ({placeholders})', values)

            # Remove archive entry after successful restore
            c.execute('DELETE FROM archived_appointments WHERE id = ?', (archived_id,))
            conn.commit()
            flash('Archived appointment restored successfully', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error restoring archived appointment', 'danger')
            current_app.logger.error(f'Error restoring archived appointment {archived_id}: {str(e)}')
        finally:
            conn.close()

        return redirect(url_for('admin_archived_appointments'))

    @app.route('/admin/archived-appointments/<int:archived_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_archived_appointment(archived_id):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("PRAGMA table_info(archived_appointments)")
            if not c.fetchall():
                flash('No archived appointments exist.', 'danger')
                return redirect(url_for('admin_archived_appointments'))

            c.execute('SELECT id FROM archived_appointments WHERE id = ?', (archived_id,))
            if not c.fetchone():
                flash('Archived appointment not found', 'danger')
                return redirect(url_for('admin_archived_appointments'))
            c.execute('DELETE FROM archived_appointments WHERE id = ?', (archived_id,))
            conn.commit()
            flash('Archived record deleted permanently', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error deleting archived record', 'danger')
            current_app.logger.error(f'Error deleting archived appointment {archived_id}: {str(e)}')
        finally:
            conn.close()

        return redirect(url_for('admin_archived_appointments'))

    @app.route('/logout')
    def logout():
        # Clear session user info
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        # Remove any queued flash messages so they don't appear after logout
        session.pop('_flashes', None)
        # Optionally remove in-progress appointment details from session
        session.pop('appointment_details', None)
        # Notify user of successful logout
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('login'))

    @app.route('/admin/logout')
    def admin_logout():
        session.pop(ADMIN_SESSION_KEY, None)
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/users/bulk-delete', methods=['POST'])
    @admin_required
    def admin_bulk_delete_users():
        if 'confirm' in request.form:
            user_ids = request.form.get('user_ids', '')
            if not user_ids:
                flash('No users selected for deletion.', 'danger')
                return redirect(url_for('admin_users'))

            user_id_list = [int(uid.strip()) for uid in user_ids.split(',') if uid.strip()]

            conn = get_db()
            c = conn.cursor()

            try:
                # Get user names for confirmation message
                placeholders = ','.join(['?'] * len(user_id_list))
                c.execute(f'SELECT id, name FROM users WHERE id IN ({placeholders})', user_id_list)
                users_to_delete = c.fetchall()

                if not users_to_delete:
                    flash('No valid users found for deletion.', 'danger')
                    return redirect(url_for('admin_users'))

                # Delete related records first (due to foreign key constraints)
                for user_id in user_id_list:
                    c.execute('DELETE FROM user_vaccine_records WHERE user_id = ?', (user_id,))
                    c.execute('DELETE FROM appointments WHERE user_id = ?', (user_id,))
                    c.execute('DELETE FROM user_documents WHERE user_id = ?', (user_id,))
                    c.execute('DELETE FROM user_activity WHERE user_id = ?', (user_id,))

                # Delete the users
                c.execute(f'DELETE FROM users WHERE id IN ({placeholders})', user_id_list)

                deleted_count = c.rowcount
                conn.commit()

                user_names = [user[1] for user in users_to_delete]
                flash(f'Successfully deleted {deleted_count} user(s): {", ".join(user_names)}', 'success')

            except Exception as e:
                conn.rollback()
                flash(f'Error deleting users: {str(e)}', 'danger')
                current_app.logger.error(f'Error bulk deleting users: {str(e)}')

            finally:
                conn.close()

    # FAQ Management Routes
    @app.route('/admin/faq', endpoint='admin_faq_list')
    @admin_required
    def admin_faq():
        conn = get_db()
        c = conn.cursor()

        # Get all FAQs ordered by display_order
        c.execute('''
            SELECT id, question, category, is_active, display_order
            FROM faq
            ORDER BY display_order ASC, id ASC
        ''')
        faqs = c.fetchall()
        conn.close()

        return render_template('admin_faq.html', faqs=faqs)

    @app.route('/admin/faq/add', methods=['GET', 'POST'], endpoint='admin_faq_add')
    @admin_required
    def admin_add_faq():
        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            answer = request.form.get('answer', '').strip()
            category = request.form.get('category', '').strip()
            display_order = request.form.get('display_order', 0)

            # Validate required fields
            if not question or not answer:
                flash('Question and answer are required.', 'danger')
                return redirect(url_for('admin_add_faq'))

            # Get the next display order if not specified
            if not display_order:
                conn = get_db()
                c = conn.cursor()
                c.execute('SELECT MAX(display_order) FROM faq')
                max_order = c.fetchone()[0]
                display_order = (max_order + 1) if max_order else 0
                conn.close()

            # Insert new FAQ
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO faq (question, answer, category, is_active, display_order, created_at)
                    VALUES (?, ?, ?, 1, ?, datetime('now'))
                ''', (question, answer, category, display_order))
                conn.commit()
                flash('FAQ added successfully!', 'success')
                return redirect(url_for('admin_faq'))
            except Exception as e:
                conn.rollback()
                flash(f'Error adding FAQ: {str(e)}', 'danger')
                current_app.logger.error(f'Error adding FAQ: {str(e)}')
            finally:
                conn.close()

        # GET request - show form
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT DISTINCT category FROM faq ORDER BY category')
        categories = [row[0] for row in c.fetchall()]
        conn.close()

        # Add default categories if none exist
        if not categories:
            categories = ['General', 'Services', 'Appointments', 'Vaccinations']

        return render_template('admin_faq_form.html', categories=categories)

    @app.route('/admin/faq/edit/<int:faq_id>', methods=['GET', 'POST'], endpoint='admin_faq_edit')
    @admin_required
    def admin_edit_faq(faq_id):
        conn = get_db()
        c = conn.cursor()

        # Get FAQ data
        c.execute('SELECT * FROM faq WHERE id = ?', (faq_id,))
        faq = c.fetchone()

        if not faq:
            conn.close()
            flash('FAQ not found.', 'danger')
            return redirect(url_for('admin_faq'))

        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            answer = request.form.get('answer', '').strip()
            category = request.form.get('category', '').strip()
            display_order = request.form.get('display_order', 0)
            is_active = 1 if request.form.get('is_active') else 0

            # Validate required fields
            if not question or not answer:
                flash('Question and answer are required.', 'danger')
                return redirect(url_for('admin_edit_faq', faq_id=faq_id))

            try:
                c.execute('''
                    UPDATE faq
                    SET question = ?, answer = ?, category = ?, display_order = ?, is_active = ?, updated_at = datetime('now')
                    WHERE id = ?
                ''', (question, answer, category, display_order, is_active, faq_id))
                conn.commit()
                flash('FAQ updated successfully!', 'success')
                return redirect(url_for('admin_faq'))
            except Exception as e:
                conn.rollback()
                flash(f'Error updating FAQ: {str(e)}', 'danger')
                current_app.logger.error(f'Error updating FAQ {faq_id}: {str(e)}')
            finally:
                conn.close()
        else:
            conn.close()

        # GET request - show form with existing data
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT DISTINCT category FROM faq ORDER BY category')
        categories = [row[0] for row in c.fetchall()]
        conn.close()

        # Add default categories if none exist
        if not categories:
            categories = ['General', 'Services', 'Appointments', 'Vaccinations']

        return render_template('admin_faq_form.html', faq=faq, categories=categories)

    @app.route('/admin/faq/delete/<int:faq_id>', methods=['POST'], endpoint='admin_faq_delete')
    @admin_required
    def admin_delete_faq(faq_id):
        conn = get_db()
        c = conn.cursor()

        try:
            # Check if FAQ exists
            c.execute('SELECT question FROM faq WHERE id = ?', (faq_id,))
            faq = c.fetchone()

            if not faq:
                flash('FAQ not found.', 'danger')
                return redirect(url_for('admin_faq'))

            # Delete the FAQ
            c.execute('DELETE FROM faq WHERE id = ?', (faq_id,))
            conn.commit()

            flash(f'FAQ "{faq[0][:50]}..." deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting FAQ: {str(e)}', 'danger')
            current_app.logger.error(f'Error deleting FAQ {faq_id}: {str(e)}')
        finally:
            conn.close()

        return redirect(url_for('admin_faq'))

    @app.route('/admin/faq/toggle/<int:faq_id>', methods=['POST'], endpoint='admin_faq_toggle')
    @admin_required
    def admin_toggle_faq(faq_id):
        conn = get_db()
        c = conn.cursor()

        try:
            # Check if FAQ exists and get current status
            c.execute('SELECT question, is_active FROM faq WHERE id = ?', (faq_id,))
            faq = c.fetchone()

            if not faq:
                flash('FAQ not found.', 'danger')
                return redirect(url_for('admin_faq'))

            # Toggle the status
            new_status = 0 if faq[1] else 1
            status_text = 'activated' if new_status else 'deactivated'

            c.execute('UPDATE faq SET is_active = ?, updated_at = datetime("now") WHERE id = ?', (new_status, faq_id))
            conn.commit()

            flash(f'FAQ "{faq[0][:50]}..." {status_text} successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating FAQ status: {str(e)}', 'danger')
            current_app.logger.error(f'Error toggling FAQ {faq_id}: {str(e)}')
        finally:
            conn.close()

        return redirect(url_for('admin_faq'))
