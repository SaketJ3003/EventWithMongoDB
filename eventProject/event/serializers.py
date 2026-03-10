from rest_framework import serializers
from .models import Event, EventImages


class FeatureImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ('id', 'title', 'feature_image')
        read_only_fields = ('id', 'title')

    def validate_feature_image(self, value):
        # print(value)
        # print(self)
        allowed = ['image/jpeg', 'image/png', 'image/jpg']
        if hasattr(value, 'content_type') and value.content_type not in allowed:
            raise serializers.ValidationError(
                'Unsupported image format. Allowed: JPEG, PNG, JPG.'
            )
        max_size = 5 * 1024 * 1024 
        if value.size > max_size:
            raise serializers.ValidationError('Image size must not exceed 5 MB.')
        return value


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImages
        fields = ('id', 'image', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_image(self, value):
        allowed = ['image/jpeg', 'image/png', 'image/jpg']
        if hasattr(value, 'content_type') and value.content_type not in allowed:
            raise serializers.ValidationError(
                'Unsupported image format. Allowed: JPEG, PNG, JPG.'
            )
        max_size = 5 * 1024 * 1024  # 5 MB
        if value.size > max_size:
            raise serializers.ValidationError('Image size must not exceed 5 MB.')
        return value


class ExtraImagesResponseSerializer(serializers.ModelSerializer):
    extra_images = EventImageSerializer(source='extraImages', many=True, read_only=True)

    class Meta:
        model = Event
        fields = ('id', 'title', 'extra_images')
