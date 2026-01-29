"""
Twilio OTP Authentication Helper
Handles phone number authentication with SMS OTP verification using Twilio
"""

import os
import secrets
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


class TwilioOTPAuth:
    """Handle OTP authentication using Twilio"""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.verify_service_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID')

        if not all([self.account_sid, self.auth_token]):
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")

        self.client = Client(self.account_sid, self.auth_token)

        # Use Twilio Verify if service SID is provided, otherwise use SMS
        self.use_verify = bool(self.verify_service_sid)

        # In-memory OTP storage (in production, use Redis or database)
        self.otp_store = {}

        # Session storage (in production, use database)
        self.sessions = {}

    def _generate_otp(self):
        """Generate a 6-digit OTP"""
        return str(secrets.randbelow(1000000)).zfill(6)

    def _generate_session_token(self):
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)

    def send_otp_verify(self, phone_number):
        """Send OTP using Twilio Verify service"""
        try:
            verification = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verifications \
                .create(to=phone_number, channel='sms')

            return {
                'success': True,
                'status': verification.status,
                'message': f'Verification code sent to {phone_number}'
            }

        except TwilioRestException as e:
            return {
                'success': False,
                'error_code': e.code,
                'error_message': e.msg
            }

    def verify_otp_verify(self, phone_number, code):
        """Verify OTP using Twilio Verify service"""
        try:
            verification_check = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verification_checks \
                .create(to=phone_number, code=code)

            if verification_check.status == 'approved':
                # Create session token
                session_token = self._generate_session_token()
                self.sessions[session_token] = {
                    'phone_number': phone_number,
                    'expires_at': datetime.now() + timedelta(hours=24)
                }

                return {
                    'success': True,
                    'session_token': session_token,
                    'phone_number': phone_number
                }
            else:
                return {
                    'success': False,
                    'error_message': 'Invalid verification code'
                }

        except TwilioRestException as e:
            return {
                'success': False,
                'error_code': e.code,
                'error_message': e.msg
            }

    def send_otp_sms(self, phone_number):
        """Send OTP via SMS (without Verify service)"""
        try:
            # Generate OTP
            otp = self._generate_otp()

            # Store OTP with expiration
            self.otp_store[phone_number] = {
                'code': otp,
                'expires_at': datetime.now() + timedelta(minutes=10)
            }

            # Send SMS
            message = self.client.messages.create(
                body=f'Your verification code is: {otp}',
                from_=self.from_number,
                to=phone_number
            )

            return {
                'success': True,
                'message_sid': message.sid,
                'message': f'Verification code sent to {phone_number}'
            }

        except TwilioRestException as e:
            return {
                'success': False,
                'error_code': e.code,
                'error_message': e.msg
            }

    def verify_otp_sms(self, phone_number, code):
        """Verify OTP sent via SMS"""
        stored = self.otp_store.get(phone_number)

        if not stored:
            return {
                'success': False,
                'error_message': 'No verification code found for this number'
            }

        # Check expiration
        if datetime.now() > stored['expires_at']:
            del self.otp_store[phone_number]
            return {
                'success': False,
                'error_message': 'Verification code expired'
            }

        # Check code
        if stored['code'] != code:
            return {
                'success': False,
                'error_message': 'Invalid verification code'
            }

        # Success - remove OTP and create session
        del self.otp_store[phone_number]

        session_token = self._generate_session_token()
        self.sessions[session_token] = {
            'phone_number': phone_number,
            'expires_at': datetime.now() + timedelta(hours=24)
        }

        return {
            'success': True,
            'session_token': session_token,
            'phone_number': phone_number
        }

    def send_otp(self, phone_number):
        """Send OTP (uses Verify service if available, otherwise SMS)"""
        if self.use_verify:
            return self.send_otp_verify(phone_number)
        else:
            if not self.from_number:
                return {
                    'success': False,
                    'error_message': 'TWILIO_PHONE_NUMBER not configured'
                }
            return self.send_otp_sms(phone_number)

    def verify_otp(self, phone_number, code):
        """Verify OTP"""
        if self.use_verify:
            return self.verify_otp_verify(phone_number, code)
        else:
            return self.verify_otp_sms(phone_number, code)

    def get_session(self, session_token):
        """Get session information"""
        session = self.sessions.get(session_token)

        if not session:
            return {
                'success': False,
                'error_message': 'Invalid session token'
            }

        # Check expiration
        if datetime.now() > session['expires_at']:
            del self.sessions[session_token]
            return {
                'success': False,
                'error_message': 'Session expired'
            }

        return {
            'success': True,
            'phone_number': session['phone_number']
        }

    def invalidate_session(self, session_token):
        """Invalidate a session (logout)"""
        if session_token in self.sessions:
            del self.sessions[session_token]

        return {
            'success': True,
            'message': 'Session invalidated'
        }

    def resend_otp(self, phone_number):
        """Resend OTP code"""
        return self.send_otp(phone_number)
