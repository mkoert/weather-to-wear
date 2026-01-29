"""
Cognito OTP Authentication Helper
Handles phone number authentication with SMS OTP verification
"""

import os
import boto3
from botocore.exceptions import ClientError


class CognitoOTPAuth:
    """Handle Cognito authentication with OTP"""

    def __init__(self):
        self.region = os.getenv('AWS_COGNITO_REGION', 'us-east-2')
        self.user_pool_id = os.getenv('AWS_COGNITO_USER_POOL_ID')
        self.client_id = os.getenv('AWS_COGNITO_CLIENT_ID')

        if not self.user_pool_id or not self.client_id:
            raise ValueError("AWS_COGNITO_USER_POOL_ID and AWS_COGNITO_CLIENT_ID must be set")

        self.client = boto3.client('cognito-idp', region_name=self.region)

    def sign_up(self, phone_number, password, name=None):
        """
        Sign up a new user with phone number

        Args:
            phone_number (str): Phone number in E.164 format (e.g., +12125551234)
            password (str): Temporary password
            name (str, optional): User's name

        Returns:
            dict: Response from Cognito with user_sub and delivery info
        """
        try:
            attributes = [
                {'Name': 'phone_number', 'Value': phone_number}
            ]

            if name:
                attributes.append({'Name': 'name', 'Value': name})

            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=phone_number,
                Password=password,
                UserAttributes=attributes
            )

            return {
                'success': True,
                'user_sub': response['UserSub'],
                'code_delivery': response.get('CodeDeliveryDetails', {}),
                'user_confirmed': response.get('UserConfirmed', False)
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def confirm_sign_up(self, phone_number, confirmation_code):
        """
        Confirm sign up with SMS code

        Args:
            phone_number (str): Phone number used for sign up
            confirmation_code (str): 6-digit code from SMS

        Returns:
            dict: Success status and message
        """
        try:
            self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=phone_number,
                ConfirmationCode=confirmation_code
            )

            return {
                'success': True,
                'message': 'Phone number verified successfully'
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def sign_in(self, phone_number, password):
        """
        Sign in with phone number and password

        Args:
            phone_number (str): Phone number in E.164 format
            password (str): User's password

        Returns:
            dict: Authentication result with tokens or challenge
        """
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': phone_number,
                    'PASSWORD': password
                }
            )

            # Check if MFA is required
            if response.get('ChallengeName') == 'SMS_MFA':
                return {
                    'success': True,
                    'requires_mfa': True,
                    'session': response['Session'],
                    'challenge_name': response['ChallengeName']
                }

            # Direct success - no MFA
            return {
                'success': True,
                'requires_mfa': False,
                'tokens': {
                    'access_token': response['AuthenticationResult']['AccessToken'],
                    'id_token': response['AuthenticationResult']['IdToken'],
                    'refresh_token': response['AuthenticationResult']['RefreshToken']
                }
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def verify_mfa_code(self, phone_number, mfa_code, session):
        """
        Verify MFA code sent via SMS

        Args:
            phone_number (str): Phone number
            mfa_code (str): 6-digit MFA code from SMS
            session (str): Session token from sign_in response

        Returns:
            dict: Authentication tokens if successful
        """
        try:
            response = self.client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName='SMS_MFA',
                Session=session,
                ChallengeResponses={
                    'USERNAME': phone_number,
                    'SMS_MFA_CODE': mfa_code
                }
            )

            return {
                'success': True,
                'tokens': {
                    'access_token': response['AuthenticationResult']['AccessToken'],
                    'id_token': response['AuthenticationResult']['IdToken'],
                    'refresh_token': response['AuthenticationResult']['RefreshToken']
                }
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def get_user_info(self, access_token):
        """
        Get user information from access token

        Args:
            access_token (str): Access token from authentication

        Returns:
            dict: User attributes
        """
        try:
            response = self.client.get_user(
                AccessToken=access_token
            )

            # Convert attributes list to dict
            attributes = {}
            for attr in response.get('UserAttributes', []):
                attributes[attr['Name']] = attr['Value']

            return {
                'success': True,
                'username': response['Username'],
                'attributes': attributes
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def resend_confirmation_code(self, phone_number):
        """
        Resend confirmation code to phone number

        Args:
            phone_number (str): Phone number to send code to

        Returns:
            dict: Delivery information
        """
        try:
            response = self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=phone_number
            )

            return {
                'success': True,
                'code_delivery': response.get('CodeDeliveryDetails', {})
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def sign_out(self, access_token):
        """
        Sign out user (global sign out)

        Args:
            access_token (str): User's access token

        Returns:
            dict: Success status
        """
        try:
            self.client.global_sign_out(
                AccessToken=access_token
            )

            return {
                'success': True,
                'message': 'Successfully signed out'
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }
