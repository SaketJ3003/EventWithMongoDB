import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventProject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
import json
from graphql_jwt.shortcuts import get_token

u = User.objects.filter(is_superuser=True).first()
token = get_token(u)

client = Client()
query = '''
query($page:Int,$ps:Int,$s:String,$st:String){
      allBookings(page:$page,pageSize:$ps,search:$s,status:$st){
        results{id bookingReference user{username email firstName lastName} event{title} ticket{price} quantity totalPrice status createdAt}
        totalCount numPages currentPage
      }
    }
'''
resp = client.post('/graphql/', 
    json.dumps({'query': query, 'variables': {'page': 1, 'ps': 15, 's': None, 'st': None}}),
    content_type='application/json',
    HTTP_AUTHORIZATION=f'JWT {token}'
)

print(resp.status_code)
print(resp.json())
