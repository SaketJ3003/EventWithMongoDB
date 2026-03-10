from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class UserToken(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='active_token')
    access_token  = models.TextField()
    refresh_token = models.TextField()
    created_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_tokens"

    def __str__(self):
        return f"Token for {self.user.username}"


class Category(models.Model):
    name = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    isActive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class EventTag(models.Model):
    name = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    isActive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class EventImages(models.Model):
    image = models.ImageField(upload_to='events/extra-images/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Event Image - {self.id}"


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class State(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'country']
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class City(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Cities"
        unique_together = ['name', 'state']
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class Event(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    feature_image = models.ImageField(upload_to='events/', blank=True, null=True)
    category = models.ManyToManyField(Category, related_name='events')
    tags = models.ManyToManyField(EventTag, related_name='events', blank=True)
    extraImages = models.ManyToManyField(EventImages, related_name='events', blank=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name='events')
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name='events')
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='events')
    venue = models.CharField(max_length=200)
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    short_description = models.CharField(max_length=255)
    long_description = models.TextField()
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 2
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
