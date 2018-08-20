from rest_framework import serializers
from realty.models import Property

class PropertySerializer(serializers.ModelSerializer):
	url = serializers.URLField(source='get_absolute_url')
	category =  serializers.StringRelatedField()
	cover = serializers.URLField(source='get_cover')
	purpose = serializers.SlugRelatedField(slug_field='activity', read_only=True)	
	phone = serializers.CharField(source='user.profile.phone')
	stars = serializers.IntegerField(default=5)
	reviews = serializers.IntegerField(default=11)
	longitude = serializers.FloatField(source='geopoint.x')
	latitude = serializers.FloatField(source='geopoint.y')
	user_avatar = serializers.URLField(source='user.profile.get_avatar')
	user_url = serializers.URLField(source='user.profile.get_absolute_url')

	class Meta:
		model = Property
		fields = (
			'url', 'category','address', 'purpose', 
			'category', 'cover', 'stars', 'reviews', 'phone', 
			'longitude', 'latitude', 'user_avatar', 'user_url'
		)