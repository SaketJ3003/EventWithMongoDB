import graphene
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.paginator import Paginator
from graphene_django import DjangoObjectType
from graphql_jwt.shortcuts import get_token
from graphql_jwt.refresh_token.shortcuts import create_refresh_token
from graphql_jwt.refresh_token.models import RefreshToken
from graphql_jwt.utils import get_payload, get_user_by_payload
from graphql_jwt.exceptions import JSONWebTokenError
from .models import Category, EventTag, Country, State, City, Event, UserToken, EventImages


def _revoke_all_tokens(user):
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



# Types 

class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')

class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'isActive', 'created_at', 'updated_at')


class EventTagType(DjangoObjectType):
    class Meta:
        model = EventTag
        fields = ('id', 'name', 'slug', 'isActive', 'created_at', 'updated_at')



class CountryType(DjangoObjectType):
    class Meta:
        model = Country
        fields = ('id', 'name', 'slug', 'created_at', 'updated_at')


class StateType(DjangoObjectType):
    class Meta:
        model = State
        fields = ('id', 'name', 'slug', 'country', 'created_at', 'updated_at')


class CityType(DjangoObjectType):
    class Meta:
        model = City
        fields = ('id', 'name', 'slug', 'state', 'created_at', 'updated_at')


class EventImagesType(DjangoObjectType):
    image = graphene.String()

    class Meta:
        model = EventImages
        fields = ('id', 'image', 'created_at', 'updated_at')

    def resolve_image(self, info):
        if not self.image:
            return None
        request = info.context
        return request.build_absolute_uri(f'/media/{self.image.name}')


class EventType(DjangoObjectType):
    feature_image = graphene.String()
    extra_images  = graphene.List(EventImagesType)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'slug',
            'category', 'tags',
            'country', 'state', 'city', 'venue',
            'event_date', 'start_time', 'end_time',
            'is_active', 'short_description', 'long_description',
            'views_count', 'created_at', 'updated_at',
        )

    def resolve_feature_image(self, info):
        if not self.feature_image:
            return None
        request = info.context
        return request.build_absolute_uri(f'/media/{self.feature_image.name}')

    def resolve_extra_images(self, info):
        return self.extraImages.all()

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

# Category Mutations 

class CreateCategoryMutation(graphene.Mutation):
    class Arguments:
        name     = graphene.String(required=True)
        is_active = graphene.Boolean()

    success  = graphene.Boolean()
    message  = graphene.String()
    category = graphene.Field(CategoryType)

    def mutate(self, info, name, is_active=True):
        admin_required(info)
        if Category.objects.filter(name=name).exists():
            return CreateCategoryMutation(success=False, message='Category already exists.', category=None)
        category = Category.objects.create(name=name, isActive=is_active)
        return CreateCategoryMutation(success=True, message='Category created.', category=category)


class UpdateCategoryMutation(graphene.Mutation):
    class Arguments:
        id        = graphene.ID(required=True)
        name      = graphene.String()
        slug      = graphene.String()
        is_active = graphene.Boolean()

    success  = graphene.Boolean()
    message  = graphene.String()
    category = graphene.Field(CategoryType)

    def mutate(self, info, id, name=None, slug=None, is_active=None):
        admin_required(info)
        try:
            category = Category.objects.get(pk=id)
        except Category.DoesNotExist:
            return UpdateCategoryMutation(success=False, message='Category not found.', category=None)
        if name is not None:
            if Category.objects.filter(name=name).exclude(pk=id).exists():
                return UpdateCategoryMutation(success=False, message='Category name already taken.', category=None)
            category.name = name
            category.slug = slug if slug else slugify(name)
        elif slug is not None:
            category.slug = slug
        if is_active is not None:
            category.isActive = is_active
        category.save()
        return UpdateCategoryMutation(success=True, message='Category updated.', category=category)


class DeleteCategoryMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, id):
        admin_required(info)
        try:
            Category.objects.get(pk=id).delete()
        except Category.DoesNotExist:
            return DeleteCategoryMutation(success=False, message='Category not found.')
        return DeleteCategoryMutation(success=True, message='Category deleted.')


# EventTag Mutations

class CreateTagMutation(graphene.Mutation):
    class Arguments:
        name      = graphene.String(required=True)
        is_active = graphene.Boolean()

    success   = graphene.Boolean()
    message   = graphene.String()
    event_tag = graphene.Field(EventTagType)

    def mutate(self, info, name, is_active=True):
        admin_required(info)
        if EventTag.objects.filter(name=name).exists():
            return CreateTagMutation(success=False, message='Tag already exists.', event_tag=None)
        tag = EventTag.objects.create(name=name, isActive=is_active)
        return CreateTagMutation(success=True, message='Tag created.', event_tag=tag)


class UpdateTagMutation(graphene.Mutation):
    class Arguments:
        id        = graphene.ID(required=True)
        name      = graphene.String()
        slug      = graphene.String()
        is_active = graphene.Boolean()

    success   = graphene.Boolean()
    message   = graphene.String()
    event_tag = graphene.Field(EventTagType)

    def mutate(self, info, id, name=None, slug=None, is_active=None):
        admin_required(info)
        try:
            tag = EventTag.objects.get(pk=id)
        except EventTag.DoesNotExist:
            return UpdateTagMutation(success=False, message='Tag not found.', event_tag=None)
        if name is not None:
            if EventTag.objects.filter(name=name).exclude(pk=id).exists():
                return UpdateTagMutation(success=False, message='Tag name already taken.', event_tag=None)
            tag.name = name
            tag.slug = slug if slug else slugify(name)
        elif slug is not None:
            tag.slug = slug
        if is_active is not None:
            tag.isActive = is_active
        tag.save()
        return UpdateTagMutation(success=True, message='Tag updated.', event_tag=tag)


class DeleteTagMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, id):
        admin_required(info)
        try:
            EventTag.objects.get(pk=id).delete()
        except EventTag.DoesNotExist:
            return DeleteTagMutation(success=False, message='Tag not found.')
        return DeleteTagMutation(success=True, message='Tag deleted.')


# Country Mutations 

class CreateCountryMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    country = graphene.Field(CountryType)

    def mutate(self, info, name):
        admin_required(info)
        if Country.objects.filter(name=name).exists():
            return CreateCountryMutation(success=False, message='Country already exists.', country=None)
        country = Country.objects.create(name=name)
        return CreateCountryMutation(success=True, message='Country created.', country=country)


class UpdateCountryMutation(graphene.Mutation):
    class Arguments:
        id   = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()
    country = graphene.Field(CountryType)

    def mutate(self, info, id, name=None, slug=None):
        admin_required(info)
        try:
            country = Country.objects.get(pk=id)
        except Country.DoesNotExist:
            return UpdateCountryMutation(success=False, message='Country not found.', country=None)
        if name is not None:
            if Country.objects.filter(name=name).exclude(pk=id).exists():
                return UpdateCountryMutation(success=False, message='Country name already taken.', country=None)
            country.name = name
            country.slug = slug if slug else slugify(name)
        elif slug is not None:
            country.slug = slug
        country.save()
        return UpdateCountryMutation(success=True, message='Country updated.', country=country)


class DeleteCountryMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, id):
        admin_required(info)
        try:
            Country.objects.get(pk=id).delete()
        except Country.DoesNotExist:
            return DeleteCountryMutation(success=False, message='Country not found.')
        return DeleteCountryMutation(success=True, message='Country deleted.')


# State Mutations

class CreateStateMutation(graphene.Mutation):
    class Arguments:
        name       = graphene.String(required=True)
        country_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    state   = graphene.Field(StateType)

    def mutate(self, info, name, country_id):
        admin_required(info)
        try:
            country = Country.objects.get(pk=country_id)
        except Country.DoesNotExist:
            return CreateStateMutation(success=False, message='Country not found.', state=None)
        state = State.objects.create(name=name, country=country)
        return CreateStateMutation(success=True, message='State created.', state=state)


class UpdateStateMutation(graphene.Mutation):
    class Arguments:
        id         = graphene.ID(required=True)
        name       = graphene.String()
        slug       = graphene.String()
        country_id = graphene.ID()

    success = graphene.Boolean()
    message = graphene.String()
    state   = graphene.Field(StateType)

    def mutate(self, info, id, name=None, slug=None, country_id=None):
        admin_required(info)
        try:
            state = State.objects.get(pk=id)
        except State.DoesNotExist:
            return UpdateStateMutation(success=False, message='State not found.', state=None)
        if name is not None:
            state.name = name
            state.slug = slug if slug else slugify(name)
        elif slug is not None:
            state.slug = slug
        if country_id is not None:
            try:
                state.country = Country.objects.get(pk=country_id)
            except Country.DoesNotExist:
                return UpdateStateMutation(success=False, message='Country not found.', state=None)
        state.save()
        return UpdateStateMutation(success=True, message='State updated.', state=state)


class DeleteStateMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, id):
        admin_required(info)
        try:
            State.objects.get(pk=id).delete()
        except State.DoesNotExist:
            return DeleteStateMutation(success=False, message='State not found.')
        return DeleteStateMutation(success=True, message='State deleted.')


# City Mutations

class CreateCityMutation(graphene.Mutation):
    class Arguments:
        name     = graphene.String(required=True)
        state_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    city    = graphene.Field(CityType)

    def mutate(self, info, name, state_id):
        admin_required(info)
        try:
            state = State.objects.get(pk=state_id)
        except State.DoesNotExist:
            return CreateCityMutation(success=False, message='State not found.', city=None)
        city = City.objects.create(name=name, state=state)
        return CreateCityMutation(success=True, message='City created.', city=city)


class UpdateCityMutation(graphene.Mutation):
    class Arguments:
        id       = graphene.ID(required=True)
        name     = graphene.String()
        slug     = graphene.String()
        state_id = graphene.ID()

    success = graphene.Boolean()
    message = graphene.String()
    city    = graphene.Field(CityType)

    def mutate(self, info, id, name=None, slug=None, state_id=None):
        admin_required(info)
        try:
            city = City.objects.get(pk=id)
        except City.DoesNotExist:
            return UpdateCityMutation(success=False, message='City not found.', city=None)
        if name is not None:
            city.name = name
            city.slug = slug if slug else slugify(name)
        elif slug is not None:
            city.slug = slug
        if state_id is not None:
            try:
                city.state = State.objects.get(pk=state_id)
            except State.DoesNotExist:
                return UpdateCityMutation(success=False, message='State not found.', city=None)
        city.save()
        return UpdateCityMutation(success=True, message='City updated.', city=city)


class DeleteCityMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, id):
        admin_required(info)
        try:
            City.objects.get(pk=id).delete()
        except City.DoesNotExist:
            return DeleteCityMutation(success=False, message='City not found.')
        return DeleteCityMutation(success=True, message='City deleted.')


# Event Mutations

class CreateEventMutation(graphene.Mutation):
    class Arguments:
        title             = graphene.String(required=True)
        country_id        = graphene.ID(required=True)
        state_id          = graphene.ID(required=True)
        city_id           = graphene.ID(required=True)
        venue             = graphene.String(required=True)
        event_date        = graphene.Date(required=True)
        start_time        = graphene.Time(required=True)
        end_time          = graphene.Time(required=True)
        short_description = graphene.String(required=True)
        long_description  = graphene.String(required=True)
        category_ids      = graphene.List(graphene.ID)
        tag_ids           = graphene.List(graphene.ID)
        is_active         = graphene.Boolean()

    success = graphene.Boolean()
    message = graphene.String()
    event   = graphene.Field(EventType)

    def mutate(self, info, title, country_id, state_id, city_id,
               venue, event_date, start_time, end_time,
               short_description, long_description,
               category_ids=None, tag_ids=None, is_active=True):
        admin_required(info)
        try:
            country = Country.objects.get(pk=country_id)
            state   = State.objects.get(pk=state_id)
            city    = City.objects.get(pk=city_id)
        except (Country.DoesNotExist, State.DoesNotExist, City.DoesNotExist) as e:
            return CreateEventMutation(success=False, message=str(e), event=None)
        event = Event.objects.create(
            title=title, country=country, state=state, city=city,
            venue=venue, event_date=event_date, start_time=start_time, end_time=end_time,
            short_description=short_description, long_description=long_description,
            is_active=is_active,
        )
        if category_ids:
            event.category.set(Category.objects.filter(pk__in=category_ids))
        if tag_ids:
            event.tags.set(EventTag.objects.filter(pk__in=tag_ids))

        return CreateEventMutation(success=True, message='Event created.', event=event)

class UpdateEventMutation(graphene.Mutation):
    class Arguments:
        id                = graphene.ID(required=True)
        title             = graphene.String()
        country_id        = graphene.ID()
        state_id          = graphene.ID()
        city_id           = graphene.ID()
        venue             = graphene.String()
        event_date        = graphene.Date()
        start_time        = graphene.Time()
        end_time          = graphene.Time()
        short_description = graphene.String()
        long_description  = graphene.String()
        category_ids      = graphene.List(graphene.ID)
        tag_ids           = graphene.List(graphene.ID)
        is_active         = graphene.Boolean()
        remove_feature_image    = graphene.Boolean()
        remove_extra_image_ids  = graphene.List(graphene.ID)

    success = graphene.Boolean()
    message = graphene.String()
    event   = graphene.Field(EventType)

    def mutate(self, info, id, title=None, country_id=None, state_id=None, city_id=None,
               venue=None, event_date=None, start_time=None, end_time=None,
               short_description=None, long_description=None,
               category_ids=None, tag_ids=None, is_active=None,
               remove_feature_image=False, remove_extra_image_ids=None):
        admin_required(info)
        try:
            event = Event.objects.get(pk=id)
        except Event.DoesNotExist:
            return UpdateEventMutation(success=False, message='Event not found.', event=None)
        if title is not None:
            event.title = title
            base_slug = slugify(title)
            slug = base_slug
            counter = 2
            while Event.objects.filter(slug=slug).exclude(pk=event.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            event.slug = slug
        if venue             is not None: event.venue             = venue
        if event_date        is not None: event.event_date        = event_date
        if start_time        is not None: event.start_time        = start_time
        if end_time          is not None: event.end_time          = end_time
        if short_description is not None: event.short_description = short_description
        if long_description  is not None: event.long_description  = long_description
        if is_active         is not None: event.is_active         = is_active
        if country_id is not None:
            try:    event.country = Country.objects.get(pk=country_id)
            except Country.DoesNotExist: pass
        if state_id is not None:
            try:    event.state = State.objects.get(pk=state_id)
            except State.DoesNotExist: pass
        if city_id is not None:
            try:    event.city = City.objects.get(pk=city_id)
            except City.DoesNotExist: pass
        if remove_feature_image:
            if event.feature_image:
                event.feature_image.delete(save=False)
            event.feature_image = None
        event.save()
        if category_ids is not None:
            event.category.set(Category.objects.filter(pk__in=category_ids))
        if tag_ids is not None:
            event.tags.set(EventTag.objects.filter(pk__in=tag_ids))
        if remove_extra_image_ids:
            event.extraImages.filter(pk__in=remove_extra_image_ids).delete()
        return UpdateEventMutation(success=True, message='Event updated.', event=event)


class DeleteEventMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, id):
        admin_required(info)
        try:
            Event.objects.get(pk=id).delete()
        except Event.DoesNotExist:
            return DeleteEventMutation(success=False, message='Event not found.')
        return DeleteEventMutation(success=True, message='Event deleted.')


class PaginatedCategoryResult(graphene.ObjectType):
    results      = graphene.List(CategoryType)
    total_count  = graphene.Int()
    num_pages    = graphene.Int()
    current_page = graphene.Int()

class PaginatedTagResult(graphene.ObjectType):
    results      = graphene.List(EventTagType)
    total_count  = graphene.Int()
    num_pages    = graphene.Int()
    current_page = graphene.Int()

class PaginatedCountryResult(graphene.ObjectType):
    results      = graphene.List(CountryType)
    total_count  = graphene.Int()
    num_pages    = graphene.Int()
    current_page = graphene.Int()

class PaginatedStateResult(graphene.ObjectType):
    results      = graphene.List(StateType)
    total_count  = graphene.Int()
    num_pages    = graphene.Int()
    current_page = graphene.Int()

class PaginatedCityResult(graphene.ObjectType):
    results      = graphene.List(CityType)
    total_count  = graphene.Int()
    num_pages    = graphene.Int()
    current_page = graphene.Int()

class PaginatedEventResult(graphene.ObjectType):
    results      = graphene.List(EventType)
    total_count  = graphene.Int()
    num_pages    = graphene.Int()
    current_page = graphene.Int()


# Mutation

class Mutation(graphene.ObjectType):
    # auth
    signup               = SignupMutation.Field()
    login                = LoginMutation.Field()
    refresh_access_token = RefreshAccessTokenMutation.Field()
    # category
    create_category = CreateCategoryMutation.Field()
    update_category = UpdateCategoryMutation.Field()
    delete_category = DeleteCategoryMutation.Field()
    # event tag
    create_tag = CreateTagMutation.Field()
    update_tag = UpdateTagMutation.Field()
    delete_tag = DeleteTagMutation.Field()
    # country
    create_country = CreateCountryMutation.Field()
    update_country = UpdateCountryMutation.Field()
    delete_country = DeleteCountryMutation.Field()
    # state
    create_state = CreateStateMutation.Field()
    update_state = UpdateStateMutation.Field()
    delete_state = DeleteStateMutation.Field()
    # city
    create_city = CreateCityMutation.Field()
    update_city = UpdateCityMutation.Field()
    delete_city = DeleteCityMutation.Field()
    # event
    create_event = CreateEventMutation.Field()
    update_event = UpdateEventMutation.Field()
    delete_event = DeleteEventMutation.Field()


# Query

class Query(graphene.ObjectType):
    me = graphene.Field(UserType)

    # users
    all_users = graphene.List(UserType)

    # categories
    all_categories  = graphene.List(CategoryType)
    category_by_id  = graphene.Field(CategoryType, id=graphene.ID(required=True))
    category_by_slug = graphene.Field(CategoryType, slug=graphene.String(required=True))

    # event tags
    all_event_tags   = graphene.List(EventTagType)
    event_tag_by_id  = graphene.Field(EventTagType, id=graphene.ID(required=True))
    event_tag_by_slug = graphene.Field(EventTagType, slug=graphene.String(required=True))

    # countries
    all_countries   = graphene.List(CountryType)
    country_by_id   = graphene.Field(CountryType, id=graphene.ID(required=True))
    country_by_slug = graphene.Field(CountryType, slug=graphene.String(required=True))

    # states
    all_states      = graphene.List(StateType)
    state_by_id     = graphene.Field(StateType, id=graphene.ID(required=True))
    states_by_country = graphene.List(StateType, country_id=graphene.ID(required=True))

    # cities
    all_cities      = graphene.List(CityType)
    city_by_id      = graphene.Field(CityType, id=graphene.ID(required=True))
    cities_by_state = graphene.List(CityType, state_id=graphene.ID(required=True))

    # events
    all_events         = graphene.List(EventType)
    event_by_id        = graphene.Field(EventType, id=graphene.ID(required=True))
    event_by_slug      = graphene.Field(EventType, slug=graphene.String(required=True))
    events_by_category = graphene.List(EventType, category_id=graphene.ID(required=True))
    events_by_tag      = graphene.List(EventType, tag_id=graphene.ID(required=True))
    active_events      = graphene.List(EventType)

    # paginated queries
    paginated_categories = graphene.Field(PaginatedCategoryResult, page=graphene.Int(), page_size=graphene.Int(), search=graphene.String())
    paginated_tags       = graphene.Field(PaginatedTagResult,       page=graphene.Int(), page_size=graphene.Int(), search=graphene.String())
    paginated_countries  = graphene.Field(PaginatedCountryResult,   page=graphene.Int(), page_size=graphene.Int(), search=graphene.String())
    paginated_states     = graphene.Field(PaginatedStateResult,     page=graphene.Int(), page_size=graphene.Int(), search=graphene.String(), country_id=graphene.ID())
    paginated_cities     = graphene.Field(PaginatedCityResult,      page=graphene.Int(), page_size=graphene.Int(), search=graphene.String(), state_id=graphene.ID(), country_id=graphene.ID())
    paginated_events        = graphene.Field(PaginatedEventResult, page=graphene.Int(), page_size=graphene.Int(), search=graphene.String(), category_id=graphene.ID(), tag_id=graphene.ID(), status=graphene.String())
    paginated_active_events = graphene.Field(PaginatedEventResult, page=graphene.Int(), page_size=graphene.Int(), search=graphene.String())

    # resolvers

    def resolve_me(self, info):
        request = info.context
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token = None
        if auth_header.startswith('JWT '):
            token = auth_header[4:]
        if not token:
            return None
        try:
            payload = get_payload(token, request)
            user = get_user_by_payload(payload)
        except JSONWebTokenError:
            return None
        if not user or not user.is_active:
            return None
        return user

    def resolve_all_users(self, info):
        admin_required(info)
        return User.objects.all()

    def resolve_all_categories(self, info):
        admin_required(info)
        return Category.objects.all()

    def resolve_category_by_id(self, info, id):
        admin_required(info)
        try:
            return Category.objects.get(pk=id)
        except Category.DoesNotExist:
            return None

    def resolve_category_by_slug(self, info, slug):
        admin_required(info)
        try:
            return Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            return None

    def resolve_all_event_tags(self, info):
        admin_required(info)
        return EventTag.objects.all()

    def resolve_event_tag_by_id(self, info, id):
        admin_required(info)
        try:
            return EventTag.objects.get(pk=id)
        except EventTag.DoesNotExist:
            return None

    def resolve_event_tag_by_slug(self, info, slug):
        admin_required(info)
        try:
            return EventTag.objects.get(slug=slug)
        except EventTag.DoesNotExist:
            return None

    def resolve_all_countries(self, info):
        admin_required(info)
        return Country.objects.all()

    def resolve_country_by_id(self, info, id):
        admin_required(info)
        try:
            return Country.objects.get(pk=id)
        except Country.DoesNotExist:
            return None

    def resolve_country_by_slug(self, info, slug):
        admin_required(info)
        try:
            return Country.objects.get(slug=slug)
        except Country.DoesNotExist:
            return None

    def resolve_all_states(self, info):
        admin_required(info)
        return State.objects.all()

    def resolve_state_by_id(self, info, id):
        admin_required(info)
        try:
            return State.objects.get(pk=id)
        except State.DoesNotExist:
            return None

    def resolve_states_by_country(self, info, country_id):
        admin_required(info)
        return State.objects.filter(country_id=country_id)

    def resolve_all_cities(self, info):
        admin_required(info)
        return City.objects.all()

    def resolve_city_by_id(self, info, id):
        admin_required(info)
        try:
            return City.objects.get(pk=id)
        except City.DoesNotExist:
            return None

    def resolve_cities_by_state(self, info, state_id):
        admin_required(info)
        return City.objects.filter(state_id=state_id)

    def resolve_all_events(self, info):
        return Event.objects.all().order_by('id')

    def resolve_event_by_id(self, info, id):
        try:
            event = Event.objects.get(pk=id)
            event.views_count += 1
            event.save()
            return event
        except Event.DoesNotExist:
            return None

    def resolve_event_by_slug(self, info, slug):
        try:
            event = Event.objects.get(slug=slug)
            event.views_count += 1
            event.save()

            return event
        except Event.DoesNotExist:
            return None

    def resolve_events_by_category(self, info, category_id):
        return Event.objects.filter(category__id=category_id)

    def resolve_events_by_tag(self, info, tag_id):
        return Event.objects.filter(tags__id=tag_id)

    def resolve_active_events(self, info):
        return Event.objects.filter(is_active=True)

    def resolve_paginated_categories(self, info, page=1, page_size=10, search=None):
        admin_required(info)
        qs = Category.objects.all().order_by('id')
        if search:
            qs = qs.filter(name__icontains=search)
        paginator = Paginator(qs, page_size)
        p = paginator.get_page(page)
        return PaginatedCategoryResult(results=list(p), total_count=paginator.count, num_pages=paginator.num_pages, current_page=p.number)

    def resolve_paginated_tags(self, info, page=1, page_size=10, search=None):
        admin_required(info)
        qs = EventTag.objects.all().order_by('id')
        if search:
            qs = qs.filter(name__icontains=search)
        paginator = Paginator(qs, page_size)
        p = paginator.get_page(page)
        return PaginatedTagResult(results=list(p), total_count=paginator.count, num_pages=paginator.num_pages, current_page=p.number)

    def resolve_paginated_countries(self, info, page=1, page_size=10, search=None):
        admin_required(info)
        qs = Country.objects.all().order_by('id')
        if search:
            qs = qs.filter(name__icontains=search)
        paginator = Paginator(qs, page_size)
        p = paginator.get_page(page)
        return PaginatedCountryResult(results=list(p), total_count=paginator.count, num_pages=paginator.num_pages, current_page=p.number)

    def resolve_paginated_states(self, info, page=1, page_size=10, search=None, country_id=None):
        admin_required(info)
        qs = State.objects.all().order_by('id')
        if search:
            qs = qs.filter(name__icontains=search)
        if country_id:
            qs = qs.filter(country_id=country_id)
        paginator = Paginator(qs, page_size)
        p = paginator.get_page(page)
        return PaginatedStateResult(results=list(p), total_count=paginator.count, num_pages=paginator.num_pages, current_page=p.number)

    def resolve_paginated_cities(self, info, page=1, page_size=10, search=None, state_id=None, country_id=None):
        admin_required(info)
        qs = City.objects.all().order_by('id')
        if search:
            qs = qs.filter(name__icontains=search)
        if state_id:
            qs = qs.filter(state_id=state_id)
        elif country_id:
            qs = qs.filter(state__country_id=country_id)
        paginator = Paginator(qs, page_size)
        p = paginator.get_page(page)
        return PaginatedCityResult(results=list(p), total_count=paginator.count, num_pages=paginator.num_pages, current_page=p.number)

    def resolve_paginated_active_events(self, info, page=1, page_size=10, search=None):
        qs = Event.objects.filter(is_active=True).order_by('event_date')
        if search:
            qs = qs.filter(title__icontains=search)
        paginator = Paginator(qs, page_size)
        p = paginator.get_page(page)
        return PaginatedEventResult(results=list(p), total_count=paginator.count, num_pages=paginator.num_pages, current_page=p.number)

    def resolve_paginated_events(self, info, page=1, page_size=10, search=None, category_id=None, tag_id=None, status=None):
        admin_required(info)
        qs = Event.objects.all().order_by('id')
        if search:
            qs = qs.filter(title__icontains=search) | Event.objects.filter(slug__icontains=search)
        if category_id:
            qs = qs.filter(category__id=category_id)
        if tag_id:
            qs = qs.filter(tags__id=tag_id)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        paginator = Paginator(qs.distinct(), page_size)
        p = paginator.get_page(page)
        return PaginatedEventResult(results=list(p), total_count=paginator.count, num_pages=paginator.num_pages, current_page=p.number)


schema = graphene.Schema(query=Query, mutation=Mutation)