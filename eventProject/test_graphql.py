import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventProject.settings')
django.setup()

import graphene
from event.schema import schema
from event.models import Booking
from unittest.mock import patch

@patch('event.schema.admin_required')
def test(mock_admin):
    mock_admin.return_value = True
    query = '''
    query {
        allBookings {
            results {
                id
                bookingReference
                user { username email firstName lastName }
                event { title }
                ticket { price }
                quantity
                totalPrice
                status
                createdAt
            }
            totalCount
        }
    }
    '''
    result = schema.execute(query)
    print('Errors:', result.errors)
    if result.errors:
        for err in result.errors:
            print(err.original_error)
            import traceback
            traceback.print_tb(err.original_error.__traceback__)

test()
