from django.db import models
from django.contrib.auth.models import User

class UserToken(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='active_token')
    access_token  = models.TextField()
    refresh_token = models.TextField()
    created_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_tokens"

    def __str__(self):
        return f"Token for {self.user.username}"