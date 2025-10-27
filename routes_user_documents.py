from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app, abort, session
import os
from functools import wraps

# Create a Blueprint for user document routes
documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please log in as admin to access this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@documents_bp.route('/user/<int:user_id>')
@admin_required
def user_documents(user_id):
    """View all documents for a specific user (admin only)"""
    conn = get_db()
    c = conn.cursor()
    
    # Get user info
    c.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
    
    # Get user's documents
    c.execute('''
        SELECT * FROM user_documents 
        WHERE user_id = ? 
        ORDER BY uploaded_at DESC
    ''', (user_id,))
    documents = [dict(row) for row in c.fetchall()]
    
    return render_template('admin_user_documents.html', 
                         user=dict(user), 
                         documents=documents)

@documents_bp.route('/upload/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def upload_document(user_id):
    """Upload a new document for a user (admin only)"""
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
        if 'document' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
            
        file = request.files['document']
        description = request.form.get('description', '').strip()
        
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
            from datetime import datetime
            import uuid
            
            original_filename = file.filename
            file_ext = os.path.splitext(original_filename)[1].lower()
            filename = f"doc_{user_id}_{uuid.uuid4().hex}{file_ext}"
            filepath = os.path.join(upload_dir, filename)
            
            try:
                # Save the file
                file.save(filepath)
                
                # Get file size in bytes
                file_size = os.path.getsize(filepath)
                
                # Save to database
                c.execute('''
                    INSERT INTO user_documents 
                    (user_id, filename, original_filename, file_path, file_size, description, uploaded_at, uploaded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, 
                    filename, 
                    original_filename, 
                    f'/static/uploads/user_docs/{filename}',
                    file_size,
                    description,
                    datetime.now().isoformat(), 
                    session.get('admin_id')
                ))
                
                conn.commit()
                flash('Document uploaded successfully!', 'success')
                return redirect(url_for('documents.user_documents', user_id=user_id))
                
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f'Error uploading document: {str(e)}')
                flash('Error uploading document. Please try again.', 'danger')
        else:
            flash('Only PDF files are allowed', 'danger')
    
    return render_template('admin_upload_document.html', user=dict(user))

@documents_bp.route('/download/<int:doc_id>')
@admin_required
def download_document(doc_id):
    """Download a document (admin only)"""
    conn = get_db()
    c = conn.cursor()
    
    # Get document info
    c.execute('''
        SELECT * FROM user_documents 
        WHERE id = ?
    ''', (doc_id,))
    document = c.fetchone()
    
    if not document:
        flash('Document not found.', 'danger')
        return redirect(url_for('admin_users'))
    
    # Verify the user has permission to access this document
    # (admin can access any document)
    
    # Get the full path to the file
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'user_docs')
    file_path = os.path.join(upload_dir, document['filename'])
    
    # Check if file exists
    if not os.path.isfile(file_path):
        flash('File not found on server.', 'danger')
        return redirect(url_for('documents.user_documents', user_id=document['user_id']))
    
    # Return the file for download
    return send_from_directory(
        os.path.dirname(file_path),
        os.path.basename(file_path),
        as_attachment=True,
        download_name=document['original_filename']
    )

@documents_bp.route('/delete/<int:doc_id>', methods=['POST'])
@admin_required
def delete_document(doc_id):
    """Delete a document (admin only)"""
    if request.method == 'POST':
        conn = get_db()
        c = conn.cursor()
        
        try:
            # Get document info before deleting
            c.execute('''
                SELECT * FROM user_documents 
                WHERE id = ?
            ''', (doc_id,))
            document = c.fetchone()
            
            if not document:
                flash('Document not found.', 'danger')
                return redirect(url_for('admin_users'))
            
            # Delete the file
            file_path = os.path.join(current_app.root_path, document['file_path'].lstrip('/'))
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    current_app.logger.error(f'Error deleting file {file_path}: {str(e)}')
            
            # Delete from database
            c.execute('DELETE FROM user_documents WHERE id = ?', (doc_id,))
            conn.commit()
            
            flash('Document deleted successfully!', 'success')
            return redirect(url_for('documents.user_documents', user_id=document['user_id']))
            
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'Error deleting document: {str(e)}')
            flash('Error deleting document. Please try again.', 'danger')
            return redirect(url_for('admin_users'))
    
    return redirect(url_for('admin_users'))

def init_document_routes(app, get_db_func):
    """Initialize the document routes with the app and database function"""
    global get_db
    get_db = get_db_func
    app.register_blueprint(documents_bp)
