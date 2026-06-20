import base64
from rest_framework import serializers
from .models import Event, EventImages


def _file_to_base64(file_obj):
    """Convert an uploaded file to a base64 data URL string."""
    content_type = getattr(file_obj, 'content_type', 'image/jpeg')
    file_obj.seek(0)
    encoded = base64.b64encode(file_obj.read()).decode('utf-8')
    return f"data:{content_type};base64,{encoded}"


class FeatureImageSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    feature_image = serializers.ImageField(write_only=True, required=False)
    feature_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Event
        fields = ('id', 'title', 'feature_image', 'feature_image_url')
        read_only_fields = ('id', 'title')

    def get_feature_image_url(self, obj):
        return obj.feature_image or None

    def validate_feature_image(self, value):
        allowed = ['image/jpeg', 'image/png', 'image/jpg']
        if hasattr(value, 'content_type') and value.content_type not in allowed:
            raise serializers.ValidationError(
                'Unsupported image format. Allowed: JPEG, PNG, JPG.'
            )
        max_size = 5 * 1024 * 1024  # 5 MB
        if value.size > max_size:
            raise serializers.ValidationError('Image size must not exceed 5 MB.')
        return value

    def update(self, instance, validated_data):
        file = validated_data.pop('feature_image', None)
        if file:
            instance.feature_image = _file_to_base64(file)
            instance.save()
        return instance


class EventImageSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    image = serializers.ImageField(write_only=True, required=False)
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EventImages
        fields = ('id', 'image', 'image_url', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_image_url(self, obj):
        return obj.image or None

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

    def create(self, validated_data):
        file = validated_data.pop('image', None)
        instance = EventImages.objects.create(**validated_data)
        if file:
            instance.image = _file_to_base64(file)
            instance.save()
        return instance


class ExtraImagesResponseSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    extra_images = EventImageSerializer(source='extraImages', many=True, read_only=True)

    class Meta:
        model = Event
        fields = ('id', 'title', 'extra_images')
