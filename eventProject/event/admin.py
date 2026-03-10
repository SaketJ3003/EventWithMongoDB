from django.contrib import admin
from .models import UserToken, Category,EventTag, Event,EventImages,City,Country,State

admin.site.register(UserToken)
admin.site.register(Category)
admin.site.register(City)
admin.site.register(State)
admin.site.register(EventImages)
admin.site.register(Event)
admin.site.register(EventTag)
admin.site.register(Country)


