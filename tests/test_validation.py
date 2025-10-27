#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from routes import validate_password_strength, validate_age
from datetime import datetime, timedelta

def test_password_validation():
    """Test password strength validation"""
    print("Testing password validation:")

    test_cases = [
        ("weak", False),                    # Too short
        ("WeakPass", False),               # No number or special char
        ("WeakPass1", False),              # No special character
        ("weakpass1", False),              # No uppercase
        ("WeakPass!", False),              # No number
        ("StrongPass1!", True),            # Valid strong password
        ("MySecure123!", True),            # Another valid password
    ]

    for password, expected in test_cases:
        result = validate_password_strength(password)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: '{password}' -> {result} (expected {expected})")

    print()

def test_age_validation():
    """Test age validation"""
    print("Testing age validation:")

    test_cases = [
        ((datetime.now() - timedelta(days=12*365)).strftime('%Y-%m-%d'), False),  # Too young (12 years)
        ((datetime.now() - timedelta(days=13*365)).strftime('%Y-%m-%d'), True),   # Exactly 13
        ((datetime.now() - timedelta(days=15*365)).strftime('%Y-%m-%d'), True),   # Old enough (15 years)
        ((datetime.now() - timedelta(days=50*365)).strftime('%Y-%m-%d'), True),   # Much older
    ]

    for date_str, expected in test_cases:
        result = validate_age(date_str)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: '{date_str}' -> {result} (expected {expected})")

    print()

if __name__ == "__main__":
    test_password_validation()
    test_age_validation()
    print("All validation tests completed!")
