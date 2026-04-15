import os
import json
import logging
import base64
import traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, redirect, url_for, session, request
import anthropic
from authlib.integrations.flask_client import OAuth
from api.client import ApiClient
from utils.data_processor import get_hourly_data

# Import database connection
from db.connection import db, get_cached_data, cache_data

# Configure structured logging for k8s
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logger = logging.getLogger('weather-app')

# Import OTP auth based on provider
OTP_PROVIDER = os.getenv('OTP_PROVIDER', 'cognito').lower()

if OTP_PROVIDER == 'twilio':
    from auth.twilio_otp import TwilioOTPAuth
    AuthProvider = TwilioOTPAuth
elif OTP_PROVIDER == 'cognito':
    from auth.cognito_otp import CognitoOTPAuth
    AuthProvider = CognitoOTPAuth
else:
    raise ValueError(f"Invalid OTP_PROVIDER: {OTP_PROVIDER}. Must be 'cognito' or 'twilio'")


app = Flask(__name__, template_folder='templates')
app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', 'localhost:8080')
app.secret_key = os.environ.get('APP_SECRET_KEY') or 'fallback-dev-key' 

api_key = os.getenv('API_KEY')
base_url = os.getenv('API_BASE_URL')
location = os.getenv('LOCATION', 'grand%20rapids%20mi')
authority = os.getenv('AWS_OAUTH_AUTHORITY')
client_id = os.getenv('AWS_OAUTH_CLIENT_ID')
client_secret = os.getenv('AWS_OAUTH_CLIENT_SECRET')
metadata_url = os.getenv('AWS_OAUTH_METADATA_URL')

# Initialize API client
api_client = ApiClient(api_key=api_key, base_url=base_url)

# Initialize Anthropic client
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
if anthropic_api_key:
    anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
else:
    anthropic_client = None

# Initialize OTP Auth based on provider
try:
    otp_auth = AuthProvider()
    logger.info("OTP provider initialized: %s", OTP_PROVIDER)
except ValueError as e:
    logger.warning("OTP authentication not configured: %s", e)
    otp_auth = None

# Initialize database
try:
    db.init_tables()
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.error("Database initialization failed: %s", e, exc_info=True)
    logger.warning("Running without database. Some features may not work.")

# app.secret_key = os.urandom(24)  # Use a secure random key in production
# oauth = OAuth(app)

# oauth.register(
#   name='oidc',
#   authority=authority,
#   client_id=client_id,
#   client_secret=client_secret,
#   server_metadata_url=metadata_url,
#   client_kwargs={'scope': 'phone openid email'}
# )

# Database functions are now imported from db.connection

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weather-to-wear')
def what_to_were_index():
    return render_template('weather-to-wear/index.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

# @app.route('/login')
# def login():
#     # Alternate option to redirect to /authorize
#     redirect_uri = url_for('authorize', _external=True)
#     print(f"Redirect URI: {redirect_uri}")
#     return oauth.oidc.authorize_redirect(redirect_uri)
    # return oauth.oidc.authorize_redirect('https://weather.michaelkoert.com/aws/callback')
# @app.route('/authorize')
# def authorize():
#     token = oauth.oidc.authorize_access_token()
#     user = token['userinfo']
#     session['user'] = user
#     return redirect(url_for('index'))

# @app.route('/logout')
# def logout():
#     session.pop('user', None)
#     return redirect(url_for('index'))

# OTP Authentication Routes

@app.route('/otp/login', methods=['GET', 'POST'])
def otp_login():
    """Handle OTP login - phone number submission"""
    if request.method == 'GET':
        return render_template('auth/otp_login.html')

    if not otp_auth:
        return jsonify({"error": "OTP authentication not configured"}), 500

    data = request.get_json()
    phone_number = data.get('phone_number')

    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400

    # Handle Twilio vs Cognito differently
    if OTP_PROVIDER == 'twilio':
        # Twilio: Just send OTP
        result = otp_auth.send_otp(phone_number)

        if result['success']:
            session['pending_phone'] = phone_number
            return jsonify({
                "success": True,
                "requires_verification": True,
                "message": "Verification code sent to your phone"
            }), 200
        else:
            return jsonify({"error": result.get('error_message', 'Failed to send OTP')}), 400

    else:
        # Cognito: Sign in with password
        password = data.get('password', 'TempPassword123!')
        result = otp_auth.sign_in(phone_number, password)

    if not result['success']:
        # If user doesn't exist, try to sign them up
        if result['error_code'] in ['UserNotFoundException', 'NotAuthorizedException']:
            signup_result = otp_auth.sign_up(phone_number, password)
            if signup_result['success']:
                # Store phone number and password in session for verification
                session['pending_phone'] = phone_number
                session['pending_password'] = password
                return jsonify({
                    "success": True,
                    "requires_verification": True,
                    "message": "Verification code sent to your phone"
                }), 200
            else:
                # User might already exist but not confirmed
                if signup_result['error_code'] == 'UsernameExistsException':
                    # Resend confirmation code
                    resend_result = otp_auth.resend_confirmation_code(phone_number)
                    if resend_result['success']:
                        session['pending_phone'] = phone_number
                        session['pending_password'] = password
                        return jsonify({
                            "success": True,
                            "requires_verification": True,
                            "message": "Account exists but not verified. Verification code sent to your phone"
                        }), 200
                return jsonify({"error": signup_result['error_message']}), 400

        return jsonify({"error": result['error_message']}), 400

    # Check if MFA is required
    if result.get('requires_mfa'):
        session['mfa_session'] = result['session']
        session['pending_phone'] = phone_number
        return jsonify({
            "success": True,
            "requires_mfa": True,
            "message": "MFA code sent to your phone"
        }), 200

    # Direct login success (no MFA)
    session['user'] = {
        'phone_number': phone_number,
        'tokens': result['tokens']
    }
    return jsonify({
        "success": True,
        "redirect": url_for('index')
    }), 200


@app.route('/otp/verify', methods=['GET', 'POST'])
def otp_verify():
    """Handle OTP code verification"""
    if request.method == 'GET':
        return render_template('auth/otp_verify.html')

    if not otp_auth:
        return jsonify({"error": "OTP authentication not configured"}), 500

    data = request.get_json()
    code = data.get('code')
    phone_number = session.get('pending_phone')

    if not code or not phone_number:
        return jsonify({"error": "Verification code and phone number are required"}), 400

    # Handle Twilio vs Cognito differently
    if OTP_PROVIDER == 'twilio':
        # Twilio: Simply verify OTP
        result = otp_auth.verify_otp(phone_number, code)

        if result['success']:
            session.pop('pending_phone', None)
            session['user'] = {
                'phone_number': phone_number,
                'session_token': result['session_token']
            }
            session['logged_in'] = True
            return jsonify({
                "success": True,
                "message": "Phone verified and logged in!",
                "redirect": url_for('what_to_were_index')
            }), 200
        else:
            return jsonify({"error": result.get('error_message', 'Invalid code')}), 400

    # Cognito flow
    # Check if this is MFA verification or signup confirmation
    elif session.get('mfa_session'):
        # MFA verification
        result = otp_auth.verify_mfa_code(
            phone_number,
            code,
            session['mfa_session']
        )

        if result['success']:
            session.pop('mfa_session', None)
            session.pop('pending_phone', None)
            session['user'] = {
                'phone_number': phone_number,
                'tokens': result['tokens']
            }
            return jsonify({
                "success": True,
                "redirect": url_for('index')
            }), 200
        else:
            return jsonify({"error": result['error_message']}), 400
    else:
        # Signup confirmation
        result = otp_auth.confirm_sign_up(phone_number, code)

        if result['success']:
            # After successful verification, automatically sign in the user
            password = session.get('pending_password', 'TempPassword123!')
            signin_result = otp_auth.sign_in(phone_number, password)

            session.pop('pending_phone', None)
            session.pop('pending_password', None)

            if signin_result['success']:
                # Check if MFA is required after signup
                if signin_result.get('requires_mfa'):
                    session['mfa_session'] = signin_result['session']
                    session['pending_phone'] = phone_number
                    return jsonify({
                        "success": True,
                        "requires_mfa": True,
                        "message": "Phone verified! Now entering your MFA code..."
                    }), 200
                else:
                    # Direct login after verification
                    session['user'] = {
                        'phone_number': phone_number,
                        'tokens': signin_result['tokens']
                    }
                    return jsonify({
                        "success": True,
                        "message": "Phone verified and logged in!",
                        "redirect": url_for('index')
                    }), 200
            else:
                # Fallback - ask to login again
                return jsonify({
                    "success": True,
                    "message": "Phone verified! Please login again.",
                    "redirect": url_for('otp_login')
                }), 200
        else:
            return jsonify({"error": result['error_message']}), 400


@app.route('/otp/resend', methods=['POST'])
def otp_resend():
    """Resend OTP code"""
    if not otp_auth:
        return jsonify({"error": "OTP authentication not configured"}), 500

    phone_number = session.get('pending_phone')
    if not phone_number:
        return jsonify({"error": "No pending verification"}), 400

    if OTP_PROVIDER == 'twilio':
        result = otp_auth.resend_otp(phone_number)
    else:
        result = otp_auth.resend_confirmation_code(phone_number)

    if result['success']:
        return jsonify({
            "success": True,
            "message": "Verification code resent"
        }), 200
    else:
        return jsonify({"error": result['error_message']}), 400


@app.route('/otp/logout')
def otp_logout():
    """Handle OTP logout"""
    if 'user' in session and 'tokens' in session['user']:
        access_token = session['user']['tokens'].get('access_token')
        if access_token and otp_auth:
            otp_auth.sign_out(access_token)

    session.pop('user', None)
    session.pop('logged_in', None)
    session.pop('mfa_session', None)
    session.pop('pending_phone', None)
    return redirect(url_for('index'))

# API

## Hourly Data Endpoint
@app.route('/api/hourly-data')
def hourly_data():
    from flask import request
    import requests

    # Get zipcode from query parameter, default to configured location
    zipcode = request.args.get('zipcode')
    if zipcode:
        # Format zipcode for API
        query_location = zipcode.strip()
    else:
        # Use default location
        query_location = location

    # Check cache first
    try:
        cached = get_cached_data(query_location)
        if cached:
            logger.info("Cache hit for location=%s", query_location)
            return jsonify(cached)
    except Exception as e:
        logger.error("Cache read failed for location=%s: %s", query_location, e, exc_info=True)

    # Fetch from API if not cached
    try:
        endpoint = f'{query_location}?unitGroup=us&include=days%2Chours%2Calerts%2Ccurrent'
        data = api_client.fetch_data(endpoint)
        hourly_data_result = get_hourly_data(data, datetime)

        # Cache the result (non-fatal if it fails)
        try:
            cache_data(query_location, hourly_data_result)
        except Exception as e:
            logger.error("Cache write failed for location=%s: %s", query_location, e, exc_info=True)

        return jsonify(hourly_data_result)
    except requests.exceptions.HTTPError as e:
        logger.error("Weather API HTTP error for location=%s status=%s: %s",
                      query_location, e.response.status_code, e, exc_info=True)
        if e.response.status_code == 400:
            return jsonify({"error": "Invalid location or zipcode. Please enter a valid US zipcode or city name."}), 400
        return jsonify({"error": "Failed to fetch weather data. Please try again later."}), 500
    except Exception as e:
        logger.error("Unexpected error for location=%s: %s", query_location, e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

def parse_claude_suggestions(raw_response):
    """Parse Claude's response into a clean suggestions object.
    Handles markdown code fences and validates the expected structure."""
    cleaned = raw_response.strip()

    # Strip markdown code fences
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Claude returned non-JSON response")
        return {
            "summary": raw_response,
            "outfit": [],
            "accessories": [],
            "tips": []
        }

    # Normalize into a consistent shape
    return {
        "summary": data.get("summary", ""),
        "outfit": [
            {
                "item": item.get("item", ""),
                "description": item.get("description", ""),
                "reason": item.get("reason", "")
            }
            for item in data.get("outfit", [])
        ],
        "accessories": [
            {
                "item": acc.get("item", ""),
                "reason": acc.get("reason", "")
            }
            for acc in data.get("accessories", [])
        ],
        "tips": data.get("tips", [])
    }


## Fashion Suggestions Endpoint
@app.route('/api/fashion-suggestions', methods=['POST'])
def fashion_suggestions():
    from flask import request
    from werkzeug.utils import secure_filename

    if not anthropic_client:
        return jsonify({"error": "Claude API not configured. Please set ANTHROPIC_API_KEY environment variable."}), 500

    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Get weather data from form
    weather_data_str = request.form.get('weather_data')
    if not weather_data_str:
        return jsonify({"error": "No weather data provided"}), 400

    try:
        weather_data = json.loads(weather_data_str)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid weather data format"}), 400

    # Read and encode the image
    image_data = file.read()
    image_base64 = base64.standard_b64encode(image_data).decode('utf-8')

    # Determine media type
    file_extension = file.filename.rsplit('.', 1)[-1].lower()
    media_type_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    media_type = media_type_map.get(file_extension, 'image/jpeg')

    # Create weather summary
    weather_summary = f"""
Current Weather Conditions:
- Temperature: {weather_data.get('temp', 'N/A')}°F
- Feels Like: {weather_data.get('feelslike', 'N/A')}°F
- Conditions: {weather_data.get('conditions', 'N/A')}
- Humidity: {weather_data.get('humidity', 'N/A')}%
- Wind Speed: {weather_data.get('windspeed', 'N/A')} mph
- Precipitation Chance: {weather_data.get('precipprob', 'N/A')}%
- UV Index: {weather_data.get('uvindex', 'N/A')}
"""

    # Call Claude API with vision
    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"""You are a fashion advisor. Analyze the clothing items in this closet photo and suggest an outfit for the current weather.

{weather_summary}

Respond with ONLY valid JSON in this exact format (no markdown, no code fences):
{{
  "summary": "One sentence explaining the overall outfit strategy for the weather.",
  "outfit": [
    {{
      "item": "Name of clothing item",
      "description": "Brief description (color, style, etc.)",
      "reason": "Why it works for this weather"
    }}
  ],
  "accessories": [
    {{
      "item": "Accessory name",
      "reason": "Why you'd want it"
    }}
  ],
  "tips": [
    "Short practical tip for comfort in this weather"
  ]
}}

Rules:
- Only suggest items you can actually see in the photo.
- Keep outfit to 3-5 items max.
- Keep accessories to 2-3 items max.
- Keep tips to 3-4 items max.
- Be specific about colors and styles you see."""
                        }
                    ],
                }
            ],
        )

        logger.info("Claude API response received, usage=%s", message.usage)
        raw_response = message.content[0].text

        suggestions = parse_claude_suggestions(raw_response)

        return jsonify({
            "suggestions": suggestions,
            "weather": weather_data
        }), 200

    except Exception as e:
        logger.error("Claude API call failed: %s", e, exc_info=True)
        return jsonify({"error": f"Failed to get fashion suggestions: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)