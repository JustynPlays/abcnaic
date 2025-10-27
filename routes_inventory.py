from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime
from functools import wraps

# Create blueprint
inventory_bp = Blueprint('inventory', __name__)

def init_inventory_routes(app, get_db):
    
    # Helper function to get database connection
    def get_db_connection():
        return get_db()
    
    # Admin required decorator
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' not in session:
                flash('Please log in as admin to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Inventory Dashboard
    @inventory_bp.route('/inventory')
    @admin_required
    def inventory_dashboard():
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get inventory summary
        c.execute('''
            SELECT 
                c.name as category,
                COUNT(i.id) as item_count,
                SUM(CASE WHEN i.quantity <= i.min_quantity THEN 1 ELSE 0 END) as low_stock_count
            FROM inventory_categories c
            LEFT JOIN inventory_items i ON c.id = i.category_id
            GROUP BY c.id
            ORDER BY c.name
        ''')
        
        categories = c.fetchall()
        
        # Get low stock items
        c.execute('''
            SELECT i.*, c.name as category_name
            FROM inventory_items i
            JOIN inventory_categories c ON i.category_id = c.id
            WHERE i.quantity <= i.min_quantity AND i.min_quantity > 0
            ORDER BY i.quantity ASC
            LIMIT 10
        ''')
        
        low_stock_items = [dict(row) for row in c.fetchall()]
        
        # Get recent transactions
        c.execute('''
            SELECT t.*, i.name as item_name, i.unit
            FROM inventory_transactions t
            JOIN inventory_items i ON t.item_id = i.id
            ORDER BY t.created_at DESC
            LIMIT 10
        ''')
        
        recent_transactions = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        return render_template(
            'inventory/dashboard.html',
            categories=categories,
            low_stock_items=low_stock_items,
            recent_transactions=recent_transactions
        )
    
    # Inventory Items List
    @inventory_bp.route('/inventory/items')
    @admin_required
    def inventory_items():
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get filter parameters
        category_id = request.args.get('category_id', type=int)
        low_stock = request.args.get('low_stock', '0') == '1'
        
        # Build query
        query = '''
            SELECT i.*, c.name as category_name
            FROM inventory_items i
            JOIN inventory_categories c ON i.category_id = c.id
            WHERE 1=1
        '''
        params = []
        
        if category_id:
            query += ' AND i.category_id = ?'
            params.append(category_id)
            
        if low_stock:
            query += ' AND i.quantity <= i.min_quantity AND i.min_quantity > 0'
        
        query += ' ORDER BY i.name'
        
        c.execute(query, params)
        items = [dict(row) for row in c.fetchall()]
        
        # Get categories for filter dropdown
        c.execute('SELECT id, name FROM inventory_categories ORDER BY name')
        categories = c.fetchall()
        
        conn.close()
        
        return render_template(
            'inventory/items/list.html',
            items=items,
            categories=categories,
            selected_category=category_id,
            show_low_stock=low_stock
        )
    
    # Add/Edit Item Form
    @inventory_bp.route('/inventory/items/add', methods=['GET', 'POST'])
    @inventory_bp.route('/inventory/items/edit/<int:item_id>', methods=['GET', 'POST'])
    @admin_required
    def manage_inventory_item(item_id=None):
        conn = get_db_connection()
        c = conn.cursor()
        
        if request.method == 'POST':
            # Process form submission
            try:
                name = request.form['name']
                description = request.form.get('description', '')
                category_id = request.form.get('category_id')
                quantity = int(request.form.get('quantity', 0))
                unit = request.form.get('unit', 'pieces')
                min_quantity = int(request.form.get('min_quantity', 0))
                max_quantity = int(request.form.get('max_quantity', 0)) if request.form.get('max_quantity') else None
                location = request.form.get('location', '')
                lot_number = request.form.get('lot_number', '')
                expiration_date = request.form.get('expiration_date')
                supplier_info = request.form.get('supplier_info', '')
                notes = request.form.get('notes', '')
                
                current_time = datetime.now().isoformat()
                
                if item_id:
                    # Update existing item
                    c.execute('''
                        UPDATE inventory_items
                        SET name = ?, description = ?, category_id = ?, quantity = ?, unit = ?,
                            min_quantity = ?, max_quantity = ?, location = ?, lot_number = ?,
                            expiration_date = ?, supplier_info = ?, notes = ?, updated_at = ?
                        WHERE id = ?
                    ''', (
                        name, description, category_id, quantity, unit, min_quantity,
                        max_quantity, location, lot_number, expiration_date,
                        supplier_info, notes, current_time, item_id
                    ))
                    
                    flash('Item updated successfully!', 'success')
                else:
                    # Insert new item
                    c.execute('''
                        INSERT INTO inventory_items (
                            name, description, category_id, quantity, unit, min_quantity,
                            max_quantity, location, lot_number, expiration_date,
                            supplier_info, notes, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        name, description, category_id, quantity, unit, min_quantity,
                        max_quantity, location, lot_number, expiration_date,
                        supplier_info, notes, current_time, current_time
                    ))
                    
                    item_id = c.lastrowid
                    
                    # Record initial quantity as a transaction
                    c.execute('''
                        INSERT INTO inventory_transactions (
                            item_id, transaction_type, quantity,
                            previous_quantity, new_quantity,
                            reference_type, notes, created_by, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item_id, 'initial', quantity,
                        0, quantity,
                        'manual', 'Initial inventory', session.get('admin_id'), current_time
                    ))
                    
                    flash('Item added successfully!', 'success')
                
                conn.commit()
                return redirect(url_for('inventory.inventory_items'))
                
            except Exception as e:
                conn.rollback()
                app.logger.error(f"Error saving inventory item: {str(e)}")
                flash('An error occurred while saving the item. Please try again.', 'danger')
        
        # For GET request or if there was an error
        item = None
        if item_id:
            c.execute('''
                SELECT * FROM inventory_items 
                WHERE id = ?
            ''', (item_id,))
            
            item = dict(c.fetchone()) if c.fetchone() else None
            if not item:
                flash('Item not found.', 'danger')
                return redirect(url_for('inventory.inventory_items'))
        
        # Get categories for dropdown
        c.execute('SELECT id, name FROM inventory_categories ORDER BY name')
        categories = c.fetchall()
        
        conn.close()
        
        return render_template(
            'inventory/items/form.html',
            item=item,
            categories=categories,
            units=['vials', 'boxes', 'pieces', 'pairs', 'liters', 'milliliters', 'grams', 'kilograms']
        )
    
    # Delete Item
    @inventory_bp.route('/inventory/items/delete/<int:item_id>', methods=['POST'])
    @admin_required
    def delete_inventory_item(item_id):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            # Check if item exists
            c.execute('SELECT name FROM inventory_items WHERE id = ?', (item_id,))
            item = c.fetchone()
            
            if not item:
                flash('Item not found.', 'danger')
                return redirect(url_for('inventory.inventory_items'))
            
            # Delete related transactions first
            c.execute('DELETE FROM inventory_transactions WHERE item_id = ?', (item_id,))
            
            # Delete the item
            c.execute('DELETE FROM inventory_items WHERE id = ?', (item_id,))
            
            conn.commit()
            flash(f'Item "{item[0]}" has been deleted.', 'success')
            
        except Exception as e:
            conn.rollback()
            app.logger.error(f"Error deleting inventory item: {str(e)}")
            flash('An error occurred while deleting the item.', 'danger')
        finally:
            conn.close()
        
        return redirect(url_for('inventory.inventory_items'))
    
    # Inventory Transactions
    @inventory_bp.route('/inventory/transactions')
    @admin_required
    def inventory_transactions():
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get filter parameters
        item_id = request.args.get('item_id', type=int)
        transaction_type = request.args.get('type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build query
        query = '''
            SELECT t.*, i.name as item_name, i.unit
            FROM inventory_transactions t
            JOIN inventory_items i ON t.item_id = i.id
            WHERE 1=1
        '''
        params = []
        
        if item_id:
            query += ' AND t.item_id = ?'
            params.append(item_id)
            
        if transaction_type:
            query += ' AND t.transaction_type = ?'
            params.append(transaction_type)
            
        if start_date:
            query += ' AND t.created_at >= ?'
            params.append(f"{start_date} 00:00:00")
            
        if end_date:
            query += ' AND t.created_at <= ?'
            params.append(f"{end_date} 23:59:59")
        
        query += ' ORDER BY t.created_at DESC'
        
        # Add pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get total count for pagination
        count_query = 'SELECT COUNT(*) FROM (' + query.replace('t.*, i.name as item_name, i.unit', '1') + ')'
        c.execute(count_query, params)
        total = c.fetchone()[0]
        
        # Add pagination to the main query
        query += ' LIMIT ? OFFSET ?'
        params.extend([per_page, (page - 1) * per_page])
        
        c.execute(query, params)
        transactions = [dict(row) for row in c.fetchall()]
        
        # Get items for filter dropdown
        c.execute('SELECT id, name FROM inventory_items ORDER BY name')
        items = c.fetchall()
        
        conn.close()
        
        return render_template(
            'inventory/transactions/list.html',
            transactions=transactions,
            items=items,
            transaction_types=['in', 'out', 'adjustment', 'expired', 'initial', 'returned'],
            selected_item=item_id,
            selected_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page,
            total=total
        )
    
    # Record Inventory Transaction (e.g., stock in/out)
    @inventory_bp.route('/inventory/transactions/record', methods=['GET', 'POST'])
    @admin_required
    def record_inventory_transaction():
        if request.method == 'POST':
            conn = get_db_connection()
            c = conn.cursor()
            
            try:
                item_id = request.form['item_id']
                transaction_type = request.form['transaction_type']
                quantity = int(request.form['quantity'])
                reference_type = request.form.get('reference_type', 'manual')
                reference_id = request.form.get('reference_id')
                notes = request.form.get('notes', '')
                
                if quantity <= 0:
                    flash('Quantity must be greater than zero.', 'danger')
                    return redirect(url_for('inventory.record_inventory_transaction'))
                
                # Get current item quantity
                c.execute('SELECT quantity FROM inventory_items WHERE id = ?', (item_id,))
                item = c.fetchone()
                
                if not item:
                    flash('Item not found.', 'danger')
                    return redirect(url_for('inventory.inventory_transactions'))
                
                current_quantity = item[0]
                new_quantity = current_quantity
                
                # Calculate new quantity based on transaction type
                if transaction_type in ('in', 'returned'):
                    new_quantity = current_quantity + quantity
                elif transaction_type in ('out', 'expired'):
                    if current_quantity < quantity and transaction_type != 'adjustment':
                        flash(f'Insufficient stock. Only {current_quantity} available.', 'danger')
                        return redirect(url_for('inventory.record_inventory_transaction'))
                    new_quantity = current_quantity - quantity
                elif transaction_type == 'adjustment':
                    new_quantity = quantity
                
                # Update item quantity
                c.execute('''
                    UPDATE inventory_items
                    SET quantity = ?, updated_at = ?
                    WHERE id = ?
                ''', (new_quantity, datetime.now().isoformat(), item_id))
                
                # Record transaction
                c.execute('''
                    INSERT INTO inventory_transactions (
                        item_id, transaction_type, quantity,
                        previous_quantity, new_quantity,
                        reference_type, reference_id, notes,
                        created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item_id, transaction_type, quantity,
                    current_quantity, new_quantity,
                    reference_type, reference_id, notes,
                    session.get('admin_id'), datetime.now().isoformat()
                ))
                
                conn.commit()
                flash('Transaction recorded successfully!', 'success')
                return redirect(url_for('inventory.inventory_transactions'))
                
            except Exception as e:
                conn.rollback()
                app.logger.error(f"Error recording inventory transaction: {str(e)}")
                flash('An error occurred while recording the transaction.', 'danger')
            finally:
                conn.close()
        
        # For GET request or if there was an error
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get items for dropdown
        c.execute('SELECT id, name, unit FROM inventory_items ORDER BY name')
        items = c.fetchall()
        
        conn.close()
        
        return render_template(
            'inventory/transactions/record.html',
            items=items,
            transaction_types=[
                ('in', 'Stock In'),
                ('out', 'Stock Out'),
                ('adjustment', 'Quantity Adjustment'),
                ('expired', 'Expired/Damaged'),
                ('returned', 'Returned')
            ],
            reference_types=[
                ('manual', 'Manual Entry'),
                ('purchase', 'Purchase Order'),
                ('usage', 'Usage/Consumption'),
                ('donation', 'Donation'),
                ('other', 'Other')
            ]
        )
    
    # Inventory Reports
    @inventory_bp.route('/inventory/reports')
    @admin_required
    def inventory_reports():
        report_type = request.args.get('type', 'stock_levels')
        
        conn = get_db_connection()
        c = conn.cursor()
        
        if report_type == 'stock_levels':
            # Stock levels report
            c.execute('''
                SELECT 
                    i.id, i.name, i.quantity, i.unit, i.min_quantity, i.max_quantity,
                    c.name as category,
                    CASE 
                        WHEN i.quantity <= i.min_quantity AND i.min_quantity > 0 THEN 'danger'
                        WHEN i.quantity <= i.min_quantity * 1.5 AND i.min_quantity > 0 THEN 'warning'
                        ELSE 'success'
                    END as status
                FROM inventory_items i
                JOIN inventory_categories c ON i.category_id = c.id
                ORDER BY status, c.name, i.name
            ''')
            
            items = [dict(row) for row in c.fetchall()]
            
            return render_template(
                'inventory/reports/stock_levels.html',
                items=items,
                report_type=report_type
            )
            
        elif report_type == 'expiring_soon':
            # Expiring soon report
            days = int(request.args.get('days', 30))
            
            c.execute('''
                SELECT 
                    i.id, i.name, i.quantity, i.unit, i.expiration_date,
                    c.name as category,
                    JULIANDAY(i.expiration_date) - JULIANDAY('now') as days_until_expiry
                FROM inventory_items i
                JOIN inventory_categories c ON i.category_id = c.id
                WHERE i.expiration_date IS NOT NULL
                    AND i.expiration_date >= DATE('now')
                    AND i.expiration_date <= DATE('now', ? || ' days')
                ORDER BY i.expiration_date
            ''', (f"+{days}",))
            
            items = [dict(row) for row in c.fetchall()]
            
            return render_template(
                'inventory/reports/expiring_soon.html',
                items=items,
                report_type=report_type,
                days=days
            )
            
        elif report_type == 'usage':
            # Usage report
            start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            
            # Get item usage summary
            c.execute('''
                SELECT 
                    i.id, i.name, i.unit,
                    COALESCE(SUM(CASE WHEN t.transaction_type = 'in' THEN t.quantity ELSE 0 END), 0) as total_in,
                    COALESCE(SUM(CASE WHEN t.transaction_type IN ('out', 'expired') THEN t.quantity ELSE 0 END), 0) as total_out,
                    (COALESCE(SUM(CASE WHEN t.transaction_type = 'in' THEN t.quantity ELSE 0 END), 0) -
                     COALESCE(SUM(CASE WHEN t.transaction_type IN ('out', 'expired') THEN t.quantity ELSE 0 END), 0)) as net_change
                FROM inventory_items i
                LEFT JOIN inventory_transactions t ON i.id = t.item_id
                    AND t.created_at BETWEEN ? AND ?
                GROUP BY i.id, i.name, i.unit
                HAVING total_in > 0 OR total_out > 0
                ORDER BY i.name
            ''', (f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
            
            usage_summary = [dict(row) for row in c.fetchall()]
            
            return render_template(
                'inventory/reports/usage.html',
                usage_summary=usage_summary,
                report_type=report_type,
                start_date=start_date,
                end_date=end_date
            )
        
        conn.close()
        return redirect(url_for('inventory.inventory_dashboard'))

    app.register_blueprint(inventory_bp, url_prefix='/admin')
