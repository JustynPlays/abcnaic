#!/usr/bin/env python3
"""Small helper to test sending an SMS using utils.sms.send_message.
Usage:
  # set env var TEST_SMS_TO or pass phone as first arg
  python test_send_sms.py "+63917xxxxxxx"
Or:
  $env:TEST_SMS_TO = "+63917xxxxxxx"; python test_send_sms.py
"""
import os
import sys
from utils.sms import send_message

phone = os.getenv('TEST_SMS_TO') or (sys.argv[1] if len(sys.argv) > 1 else None)
if not phone:
    print("Usage: set TEST_SMS_TO env var or pass phone as arg (E.164 or local). Example: +639171234567")
    sys.exit(1)

body = os.getenv('TEST_SMS_BODY') or 'Test message from ABC-PWA'
print('Sending to:', phone)
res = send_message(phone, body)
print('Result:', res)
