from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from graphql_jwt.utils import get_payload, get_user_by_payload
from graphql_jwt.exceptions import JSONWebTokenError
from .models import UserToken


class UserTokenJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('JWT '):
            return None

        token = auth_header[4:] 

        try:
            payload = get_payload(token, request)
            user = get_user_by_payload(payload)
        except JSONWebTokenError as e:
            raise AuthenticationFailed(f'Invalid or expired token: {e}')

        if not user or not user.is_active:
            raise AuthenticationFailed('User not found or inactive.')

        try:
            stored = UserToken.objects.get(user=user)
        except UserToken.DoesNotExist:
            raise AuthenticationFailed('No active session found. Please log in.')

        if stored.access_token != token:
            raise AuthenticationFailed('Token has been invalidated. Please log in again.')

        return (user, token)

    def authenticate_header(self, request):
        return 'JWT'
