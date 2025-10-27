from flask import Blueprint, request, jsonify, current_app
from utils.sms import send_otp, verify_otp, normalize_phone

sms_bp = Blueprint('sms_bp', __name__)


@sms_bp.route('/send_sms_otp', methods=['POST'])
def send_sms_otp():
    data = request.get_json(force=True, silent=True) or {}
    phone = data.get('phone')
    if not phone:
        return jsonify({'ok': False, 'error': 'missing_phone'}), 400
    try:
        phone_norm = normalize_phone(phone)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_phone'}), 400

    result = send_otp(phone_norm)
    if result.get('ok'):
        return jsonify({'ok': True, 'method': result.get('method')})
    err = result.get('error', 'unknown')
    if err == 'rate_limited':
        return jsonify({'ok': False, 'error': 'rate_limited'}), 429
    if err == 'server_busy':
        return jsonify({'ok': False, 'error': 'server_busy'}), 429
    return jsonify({'ok': False, 'error': err}), 500


@sms_bp.route('/verify_sms_otp', methods=['POST'])
def verify_sms_otp():
    data = request.get_json(force=True, silent=True) or {}
    phone = data.get('phone')
    code = data.get('code')
    if not phone or not code:
        return jsonify({'ok': False, 'error': 'missing_params'}), 400
    try:
        phone_norm = normalize_phone(phone)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_phone'}), 400

    ok = verify_otp(phone_norm, code)
    if ok:
        # Optionally: mark user phone_verified in DB here
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'invalid_code'}), 400
