from rest_framework import serializers
from apps.realty.models import Property

class PropertySerializer(serializers.ModelSerializer):
    url = serializers.URLField(source='get_absolute_url')
    price = serializers.CharField(source='get_price_area')
    category = serializers.SlugRelatedField(slug_field='singular_name', read_only=True)
    cover = serializers.URLField(source='get_cover')
    purpose = serializers.CharField(source='get_purpose.activity')  
    phone = serializers.CharField(source='user.profile.phone')
    stars = serializers.IntegerField(default=5)
    reviews = serializers.IntegerField(default=11)
    longitude = serializers.FloatField(source='get_longitude')
    latitude = serializers.FloatField(source='get_latitude')
    user_avatar = serializers.URLField(source='user.profile.get_avatar')
    user_url = serializers.URLField(source='user.profile.get_absolute_url')
    user_name = serializers.CharField(source='user.first_name')
    list_card = serializers.CharField(source='render_list_card')

    class Meta:
        model = Property
        fields = (
            'url', 'price','category','address', 'purpose', 
            'category', 'cover', 'stars', 'reviews', 'phone', 
            'longitude', 'latitude', 'user_avatar', 'user_url',
            'user_name', 'list_card',
        )