"""
Custom Cloudinary storage backend for Django 6.0+.
Uses the cloudinary package directly — no django-cloudinary-storage needed.
"""
import os
from io import BytesIO
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible


@deconstructible
class CloudinaryStorage(Storage):
    """
    Django storage backend that saves media files to Cloudinary.
    Compatible with Django 6.0+ STORAGES dict configuration.
    """

    def _get_public_id(self, name):
        """Convert file path to cloudinary public_id (strip extension for images)."""
        # Normalize slashes
        name = name.replace('\\', '/')
        root, ext = os.path.splitext(name)
        return root

    def _open(self, name, mode='rb'):
        import urllib.request
        file_url = self.url(name)
        with urllib.request.urlopen(file_url) as resp:
            return ContentFile(resp.read(), name=name)

    def _save(self, name, content):
        import cloudinary.uploader
        public_id = self._get_public_id(name)
        content.seek(0)
        cloudinary.uploader.upload(
            content,
            public_id=public_id,
            overwrite=True,
            resource_type='image',
        )
        return name

    def delete(self, name):
        import cloudinary.uploader
        try:
            cloudinary.uploader.destroy(
                self._get_public_id(name),
                resource_type='image'
            )
        except Exception:
            pass

    def exists(self, name):
        import cloudinary.api
        try:
            cloudinary.api.resource(self._get_public_id(name))
            return True
        except Exception:
            return False

    def url(self, name):
        import cloudinary
        public_id = self._get_public_id(name)
        # Build a secure HTTPS URL
        return f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/image/upload/{public_id}"

    def size(self, name):
        import cloudinary.api
        try:
            res = cloudinary.api.resource(self._get_public_id(name))
            return res.get('bytes', 0)
        except Exception:
            return 0

    def get_available_name(self, name, max_length=None):
        # Cloudinary handles overwriting by public_id — return name as-is
        return name
