from django.urls import path
from .views import FeatureImageUploadView, ExtraImagesUploadView, login_page, signup_page, event_list_page, event_detail_page

urlpatterns = [
    path('login/',  login_page,  name='login'),
    path('signup/', signup_page, name='signup'),
    path('events/', event_list_page,   name='event-list'),
    path('events/<slug:slug>/', event_detail_page, name='event-detail'),
    path('events/<str:event_id>/feature-image/', FeatureImageUploadView.as_view(), name='event-feature-image'),
    path('events/<str:event_id>/extra-images/', ExtraImagesUploadView.as_view(), name='event-extra-images'),
]