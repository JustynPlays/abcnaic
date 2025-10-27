#!/usr/bin/env python3
import sqlite3
import os
import sys

def test_faq_functionality():
    """Test FAQ functionality"""
    try:
        # Test database connection
        db_path = 'animal_bite_center.db'
        if not os.path.exists(db_path):
            print("Database file not found!")
            return False

        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Check if FAQ table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='faq'")
        table = c.fetchone()

        if not table:
            print("FAQ table does not exist!")
            conn.close()
            return False

        print("✓ FAQ table exists")

        # Count FAQs
        c.execute('SELECT COUNT(*) FROM faq')
        count = c.fetchone()[0]
        print(f"✓ Number of FAQs: {count}")

        # Test sample FAQ retrieval
        c.execute('SELECT id, question, category, is_active FROM faq LIMIT 3')
        faqs = c.fetchall()

        if faqs:
            print("✓ Sample FAQs retrieved successfully:")
            for faq in faqs:
                print(f"  - ID: {faq[0]}, Question: {faq[1][:50]}..., Category: {faq[2]}, Active: {faq[3]}")
        else:
            print("⚠ No FAQs found in database")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ Error testing FAQ functionality: {e}")
        return False

def test_imports():
    """Test if our routes can be imported"""
    try:
        sys.path.append('.')
        from routes import init_routes
        print("✓ Routes module imported successfully")
        return True
    except Exception as e:
        print(f"✗ Error importing routes: {e}")
        return False

if __name__ == "__main__":
    print("Testing FAQ functionality...")
    faq_ok = test_faq_functionality()
    import_ok = test_imports()

    if faq_ok and import_ok:
        print("\n✓ All tests passed! FAQ system should be working.")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
