"""
SMS Utility Functions for Dr. Care Animal Bite Center

This module handles SMS functionality including:
- Sending SMS messages via Twilio
- Managing SMS templates
- Logging SMS activities
- User SMS preferences
"""

import os
import re
import logging
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSService:
    """SMS Service class for handling all SMS operations"""

    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize SMS service with app configuration"""
        self.app = app
        self.twilio_client = None

        # SMS Configuration from environment variables
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')

        # Initialize Twilio client if credentials are available
        if self.twilio_account_sid and self.twilio_auth_token:
            self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)

        # SMS Settings
        self.sms_enabled = os.getenv('SMS_ENABLED', 'true').lower() == 'true'
        self.sms_provider = os.getenv('SMS_PROVIDER', 'twilio')  # twilio, semaphore, etc.

    def is_enabled(self):
        """Check if SMS service is enabled"""
        return self.sms_enabled and self.twilio_client is not None

    def validate_phone_number(self, phone_number):
        """Validate Philippine phone number format"""
        if not phone_number:
            return False

        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone_number)

        # Philippine phone numbers should be 10 digits starting with 9
        # Or 11 digits starting with 63 (country code)
        # Or 11 digits starting with 09 (mobile format)
        if len(digits_only) == 10 and digits_only.startswith('9'):
            return True
        elif len(digits_only) == 11 and digits_only.startswith('639'):
            return True
        elif len(digits_only) == 11 and digits_only.startswith('09'):
            return True
        elif len(digits_only) == 12 and digits_only.startswith('639'):
            return True

        return False

    def format_phone_number(self, phone_number):
        """Format phone number for sending"""
        if not phone_number:
            return None

        digits_only = re.sub(r'\D', '', phone_number)

        # Add country code if not present
        if len(digits_only) == 10 and digits_only.startswith('9'):
            return f"+63{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith('639'):
            return f"+{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith('09'):
            # Convert 09XXXXXXXXX to +639XXXXXXXXX
            return f"+63{digits_only[1:]}"
        elif len(digits_only) == 12 and digits_only.startswith('639'):
            return f"+{digits_only}"

        return None

    def get_sms_template(self, template_name):
        """Get SMS template from database"""
        if not self.app:
            return None

        try:
            conn = self.app.get_db()
            c = conn.cursor()
            c.execute('''
                SELECT template_content, is_active
                FROM sms_templates
                WHERE template_name = ? AND is_active = 1
            ''', (template_name,))
            template = c.fetchone()
            conn.close()

            if template:
                return template['template_content']
        except Exception as e:
            logger.error(f"Error getting SMS template '{template_name}': {str(e)}")

        return None

    def render_template(self, template_content, variables):
        """Render template with variables"""
        try:
            for key, value in variables.items():
                template_content = template_content.replace(f"{{{{{key}}}}}", str(value))
            return template_content
        except Exception as e:
            logger.error(f"Error rendering SMS template: {str(e)}")
            return template_content

    def get_user_sms_settings(self, user_id):
        """Get user's SMS preferences"""
        if not self.app:
            return None

        try:
            conn = self.app.get_db()
            c = conn.cursor()
            c.execute('''
                SELECT * FROM sms_settings WHERE user_id = ?
            ''', (user_id,))
            settings = c.fetchone()
            conn.close()

            if settings:
                return dict(settings)
        except Exception as e:
            logger.error(f"Error getting SMS settings for user {user_id}: {str(e)}")

        return None

    def update_user_sms_settings(self, user_id, settings_data):
        """Update user's SMS preferences"""
        if not self.app:
            return False

        try:
            conn = self.app.get_db()
            c = conn.cursor()

            # Check if settings exist for user
            c.execute('SELECT id FROM sms_settings WHERE user_id = ?', (user_id,))
            existing = c.fetchone()

            if existing:
                # Update existing settings
                update_fields = []
                update_values = []

                for field, value in settings_data.items():
                    if field in ['phone_number', 'appointment_reminders', 'appointment_confirmations',
                               'vaccine_reminders', 'general_notifications', 'marketing_messages']:
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)

                if update_fields:
                    update_values.append(user_id)
                    c.execute(f'''
                        UPDATE sms_settings
                        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', update_values)
            else:
                # Create new settings
                c.execute('''
                    INSERT INTO sms_settings (user_id, phone_number, appointment_reminders,
                                            appointment_confirmations, vaccine_reminders,
                                            general_notifications, marketing_messages)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    settings_data.get('phone_number'),
                    settings_data.get('appointment_reminders', 1),
                    settings_data.get('appointment_confirmations', 1),
                    settings_data.get('vaccine_reminders', 1),
                    settings_data.get('general_notifications', 1),
                    settings_data.get('marketing_messages', 0)
                ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error updating SMS settings for user {user_id}: {str(e)}")
            return False

    def log_sms(self, user_id, phone_number, message_type, message_content, status='pending'):
        """Log SMS activity"""
        if not self.app:
            return False

        try:
            conn = self.app.get_db()
            c = conn.cursor()
            c.execute('''
                INSERT INTO sms_logs (user_id, phone_number, message_type, message_content, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, phone_number, message_type, message_content, status))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error logging SMS: {str(e)}")
            return False

    def update_sms_status(self, log_id, status, provider_response=None):
        """Update SMS log status"""
        if not self.app:
            return False

        try:
            conn = self.app.get_db()
            c = conn.cursor()

            update_data = [status]
            if provider_response:
                update_data.append(provider_response)
                update_data.append(log_id)
                c.execute('''
                    UPDATE sms_logs
                    SET status = ?, provider_response = ?, sent_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', update_data)
            else:
                update_data.append(log_id)
                c.execute('''
                    UPDATE sms_logs
                    SET status = ?, sent_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', update_data)

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating SMS status: {str(e)}")
            return False

    def send_sms(self, to_phone, message, user_id=None, message_type='general'):
        """Send SMS message"""
        if not self.is_enabled():
            logger.warning("SMS service is not enabled or configured")
            return False

        # Validate phone number
        if not self.validate_phone_number(to_phone):
            logger.error(f"Invalid phone number: {to_phone}")
            self.log_sms(user_id, to_phone, message_type, message, 'failed')
            return False

        formatted_phone = self.format_phone_number(to_phone)
        if not formatted_phone:
            logger.error(f"Could not format phone number: {to_phone}")
            self.log_sms(user_id, to_phone, message_type, message, 'failed')
            return False

        # Log the SMS attempt
        self.log_sms(user_id, formatted_phone, message_type, message, 'pending')

        try:
            # Send via Twilio
            twilio_message = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=formatted_phone
            )

            # Update log with success
            self.update_sms_status(twilio_message.sid, 'sent', str(twilio_message.status))

            logger.info(f"SMS sent successfully to {formatted_phone}")
            return True

        except TwilioException as e:
            logger.error(f"Twilio error sending SMS to {formatted_phone}: {str(e)}")
            self.update_sms_status(None, 'failed', str(e))
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SMS to {formatted_phone}: {str(e)}")
            self.update_sms_status(None, 'failed', str(e))
            return False

    def send_template_sms(self, user_id, template_name, variables, message_type=None):
        """Send SMS using template"""
        template = self.get_sms_template(template_name)
        if not template:
            logger.error(f"Template '{template_name}' not found")
            return False

        # Add user name to variables if not present
        if 'name' not in variables:
            try:
                conn = self.app.get_db()
                c = conn.cursor()
                c.execute('SELECT name FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                conn.close()
                if user:
                    variables['name'] = user['name']
            except Exception as e:
                logger.error(f"Error getting user name for SMS template: {str(e)}")

        message = self.render_template(template, variables)

        if not message_type:
            message_type = template_name

        # Get user's phone number from SMS settings
        settings = self.get_user_sms_settings(user_id)
        if not settings or not settings.get('phone_number'):
            logger.error(f"No phone number configured for user {user_id}")
            return False

        return self.send_sms(
            settings['phone_number'],
            message,
            user_id,
            message_type
        )

    def can_send_sms(self, user_id, message_type):
        """Check if user allows SMS for specific message type"""
        settings = self.get_user_sms_settings(user_id)
        if not settings:
            return False

        # Map message types to settings fields
        type_mapping = {
            'appointment_reminder': 'appointment_reminders',
            'appointment_confirmation': 'appointment_confirmations',
            'vaccine_reminder': 'vaccine_reminders',
            'verification': 'general_notifications',
            'marketing': 'marketing_messages'
        }

        setting_field = type_mapping.get(message_type, 'general_notifications')
        return bool(settings.get(setting_field, 0))

# Global SMS service instance
sms_service = SMSService()

def send_appointment_reminder(appointment_id):
    """Send appointment reminder SMS"""
    if not sms_service.is_enabled():
        return False

    try:
        conn = current_app.get_db()
        c = conn.cursor()

        # Get appointment details with user info
        c.execute('''
            SELECT a.*, u.name, u.id as user_id
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = ?
        ''', (appointment_id,))

        appointment = c.fetchone()
        conn.close()

        if not appointment:
            logger.error(f"Appointment {appointment_id} not found")
            return False

        appointment = dict(appointment)

        # Check if reminder should be sent (24 hours before appointment)
        appointment_datetime = datetime.strptime(
            f"{appointment['appointment_date']} {appointment['appointment_time']}",
            '%Y-%m-%d %H:%M'
        )

        if appointment_datetime - datetime.now() > timedelta(hours=24):
            logger.info(f"Appointment reminder for {appointment_id} not yet due")
            return False

        # Send reminder SMS
        variables = {
            'name': appointment['name'],
            'service': appointment['service'],
            'date': appointment['appointment_date'],
            'time': appointment['appointment_time']
        }

        return sms_service.send_template_sms(
            appointment['user_id'],
            'appointment_reminder',
            variables,
            'appointment_reminder'
        )

    except Exception as e:
        logger.error(f"Error sending appointment reminder: {str(e)}")
        return False

def send_appointment_confirmation(appointment_id):
    """Send appointment confirmation SMS"""
    if not sms_service.is_enabled():
        return False

    try:
        conn = current_app.get_db()
        c = conn.cursor()

        # Get appointment details with user info
        c.execute('''
            SELECT a.*, u.name, u.id as user_id
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = ?
        ''', (appointment_id,))

        appointment = c.fetchone()
        conn.close()

        if not appointment:
            logger.error(f"Appointment {appointment_id} not found")
            return False

        appointment = dict(appointment)

        # Send confirmation SMS
        variables = {
            'name': appointment['name'],
            'service': appointment['service'],
            'date': appointment['appointment_date'],
            'time': appointment['appointment_time']
        }

        return sms_service.send_template_sms(
            appointment['user_id'],
            'appointment_confirmation',
            variables,
            'appointment_confirmation'
        )

    except Exception as e:
        logger.error(f"Error sending appointment confirmation: {str(e)}")
        return False

def send_verification_code(phone_number, code, user_id=None):
    """Send verification code via SMS"""
    if not sms_service.is_enabled():
        return False

    variables = {'code': code}

    # Format phone number
    formatted_phone = sms_service.format_phone_number(phone_number)
    if not formatted_phone:
        logger.error(f"Invalid phone number for verification: {phone_number}")
        return False

    message = sms_service.render_template(
        sms_service.get_sms_template('verification_code') or 'Your verification code is: {{code}}',
        variables
    )

    return sms_service.send_sms(formatted_phone, message, user_id, 'verification')
