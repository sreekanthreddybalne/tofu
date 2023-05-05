from app.models import *
from api.serializers import *
import json

with open('data/restaurants.json', 'r') as f:
    d = json.load(f)
    restaurants = d["restaurants"]
    Restaurant.objects.all().delete()
    for index, dt in enumerate(restaurants):
        data = {"name": dt}
        serializer = RestaurantCREATESerializer(data=dt)
        if serializer.is_valid():
            serializer.save()
        else:
            print(index)
            print(serializer.errors)
