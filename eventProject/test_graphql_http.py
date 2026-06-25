import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventProject.settings')
django.setup()

import urllib.request
import json
from django.contrib.auth.models import User
from event.models import UserToken

# Get admin and their stored token
u = User.objects.filter(is_superuser=True).first()
stored = UserToken.objects.get(user=u)
token = stored.access_token
print(f"Using stored token for {u.username}: {token[:40]}...")

req = urllib.request.Request('http://127.0.0.1:8000/graphql/')
req.add_header('Content-Type', 'application/json')
req.add_header('Authorization', f'JWT {token}')

query = '''
query($page:Int,$ps:Int,$s:String,$st:String){
      allBookings(page:$page,pageSize:$ps,search:$s,status:$st){
        results{id bookingReference user{username email firstName lastName} event{title} ticket{price} quantity totalPrice status createdAt}
        totalCount numPages currentPage
      }
    }
'''

data = json.dumps({'query': query, 'variables': {'page': 1, 'ps': 15, 's': None, 'st': None}}).encode('utf-8')

try:
    with urllib.request.urlopen(req, data=data) as response:
        result = json.loads(response.read().decode('utf-8'))
        if result.get('errors'):
            print("ERRORS:", result['errors'])
        else:
            bookings = result['data']['allBookings']['results']
            print(f"SUCCESS! Got {len(bookings)} bookings")
            for b in bookings:
                user_info = b.get('user') or {}
                print(f"  - {b['bookingReference']} | {user_info.get('username','NO USER')} | {b['status']}")
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode('utf-8'))
