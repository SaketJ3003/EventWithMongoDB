from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='admin_dashboard'),
    path('categories/', views.categories, name='admin_categories'),
    path('tags/', views.tags, name='admin_tags'),
    path('countries/', views.countries, name='admin_countries'),
    path('states/', views.states, name='admin_states'),
    path('cities/', views.cities, name='admin_cities'),
    path('tickets/', views.tickets, name='admin_tickets'),
    path('bookings/', views.bookings, name='admin_bookings'),
    path('create-event/', views.create_event, name='admin_create_event'),
    path('edit-event/', views.edit_event, name='admin_edit_event'),
]
