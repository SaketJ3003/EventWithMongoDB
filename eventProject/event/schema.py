import graphene
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from graphene_django import DjangoObjectType
from graphql_jwt.shortcuts import get_token
from graphql_jwt.refresh_token.shortcuts import create_refresh_token
from graphql_jwt.refresh_token.models import RefreshToken
from graphql_jwt.utils import get_payload, get_user_by_payload
from graphql_jwt.exceptions import JSONWebTokenError
from .models import UserToken


def _revoke_all_tokens(user):
    """Delete UserToken and revoke all graphql_jwt refresh tokens for a user."""
    UserToken.objects.filter(user=user).delete()
    RefreshToken.objects.filter(user=user).delete()


def get_user_from_request(info):
    request     = info.context
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('JWT '):
        raise Exception("Authentication required. Provide a JWT token in the Authorization header.")
    token = auth_header[4:]
    try:
        payload = get_payload(token, request)
        user    = get_user_by_payload(payload)
    except JSONWebTokenError as e:
        raise Exception(f"Invalid or expired token: {e}")
    if not user or not user.is_active:
        raise Exception("User not found or inactive.")
    try:
        stored = UserToken.objects.get(user=user)
    except UserToken.DoesNotExist:
        raise Exception("No active session found. Please log in.")
    if stored.access_token != token:
        _revoke_all_tokens(user)
        raise Exception("Token has been invalidated. Please log in again.")
    return user


def admin_required(info):
    user = get_user_from_request(info)
    if not (user.is_staff or user.is_superuser):
        raise Exception("Admin access required.")
    return user


class UserType(DjangoObjectType):
    class Meta:
        model  = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')


# Auth Mutations 

class SignupMutation(graphene.Mutation):
    class Arguments:
        username   = graphene.String(required=True)
        email      = graphene.String(required=True)
        password   = graphene.String(required=True)
        first_name = graphene.String()
        last_name  = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()
    user    = graphene.Field(UserType)

    def mutate(self, info, username, email, password, first_name='', last_name=''):
        if User.objects.filter(username=username).exists():
            return SignupMutation(success=False, message='Username already exists.', user=None)
        if User.objects.filter(email=email).exists():
            return SignupMutation(success=False, message='Email already registered.', user=None)
        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name
        )
        return SignupMutation(success=True, message='User created successfully.', user=user)


class LoginMutation(graphene.Mutation):
    class Arguments:
        email    = graphene.String(required=True)
        password = graphene.String(required=True)

    success       = graphene.Boolean()
    message       = graphene.String()
    user          = graphene.Field(UserType)
    access_token  = graphene.String()
    refresh_token = graphene.String()

    def mutate(self, info, email, password):
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return LoginMutation(success=False, message='User with this email does not exist.',
                                 user=None, access_token=None, refresh_token=None)
        user = authenticate(request=info.context, username=user_obj.username, password=password)
        if user is None:
            return LoginMutation(success=False, message='Invalid credentials.',
                                 user=None, access_token=None, refresh_token=None)

        RefreshToken.objects.filter(user=user).delete()
        access_token = get_token(user)
        refresh = create_refresh_token(user)

        UserToken.objects.update_or_create(
            user=user,
            defaults={'access_token': access_token, 'refresh_token': str(refresh.token)}
        )
        return LoginMutation(success=True, message='Login successful.',
                             user=user, access_token=access_token, refresh_token=str(refresh.token))


class RefreshAccessTokenMutation(graphene.Mutation):
    class Arguments:
        refresh_token = graphene.String(required=True)

    success      = graphene.Boolean()
    message      = graphene.String()
    access_token = graphene.String()

    def mutate(self, info, refresh_token):
        try:
            token_obj = RefreshToken.objects.get(token=refresh_token)
        except RefreshToken.DoesNotExist:
            return RefreshAccessTokenMutation(success=False,
                                             message='Invalid refresh token.',
                                             access_token=None)
        if token_obj.revoked:
            _revoke_all_tokens(token_obj.user)
            return RefreshAccessTokenMutation(success=False,
                                             message='Refresh token has been revoked. Please log in again.',
                                             access_token=None)
        user = token_obj.user

        new_access_token = get_token(user)

        UserToken.objects.update_or_create(
            user=user,
            defaults={'access_token': new_access_token, 'refresh_token': refresh_token}
        )
        return RefreshAccessTokenMutation(success=True,
                                         message='Access token refreshed successfully.',
                                         access_token=new_access_token)

# Mutation

class Mutation(graphene.ObjectType):
    # auth
    signup               = SignupMutation.Field()
    login                = LoginMutation.Field()
    refresh_access_token = RefreshAccessTokenMutation.Field()


class Query(graphene.ObjectType):
    me = graphene.Field(UserType)

    def resolve_me(self, info):
        return get_user_from_request(info)


schema = graphene.Schema(query=Query, mutation=Mutation)