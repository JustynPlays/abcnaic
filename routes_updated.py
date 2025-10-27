from flask import render_template, request, redirect, url_for, session, flash, current_app, abort, send_file, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from datetime import datetime, timedelta
import sqlite3
import os
from io import BytesIO
# from utils.pdf_generator import generate_vaccine_record_pdf  # PDF generation disabled
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def init_routes(app, get_db, mail, serializer):
    # ... [previous code remains the same until the end of the file] ...

    # Admin: Upload PDF for user
    @app.route('/admin/user/<int:user_id>/upload-pdf', methods=['GET', 'POST'])
    @admin_required
    def admin_upload_user_pdf(user_id):
        conn = get_db()
        c = conn.cursor()
        
        # Get user info
        c.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_users'))
            
        if request.method == 'POST':
            # Check if the post request has the file part
            if 'pdf_file' not in request.files:
                flash('No file part', 'danger')
                return redirect(request.url)
                
            file = request.files['pdf_file']
            description = request.form.get('description', '')
            
            # If user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)
                
            if file and file.filename.lower().endswith('.pdf'):
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'user_docs')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generate a unique filename
                filename = f"doc_{user_id}_{int(datetime.now().timestamp())}.pdf"
                filepath = os.path.join(upload_dir, filename)
                
                # Save the file
                file.save(filepath)
                
                # Save to database
                c.execute('''
                    INSERT INTO user_documents 
                    (user_id, filename, original_filename, file_path, description, uploaded_at, uploaded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, filename, file.filename, f'/static/uploads/user_docs/{filename}', 
                     description, datetime.now().isoformat(), session.get('admin_id')))
                
                conn.commit()
                flash('PDF uploaded successfully!', 'success')
                return redirect(url_for('admin_user_detail', user_id=user_id))
            else:
                flash('Only PDF files are allowed', 'danger')
        
        return render_template('admin_upload_pdf.html', user=dict(user))

    return app
