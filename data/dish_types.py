from app.models import *
from api.serializers import *
import json

with open('data/dish_types.json', 'r') as f:
    d = json.load(f)
    dish_types = d["dish_types"]
    DishType.objects.all().delete()
    for index, dt in enumerate(dish_types):
        data = {"name": dt}
        serializer = DishTypeCREATESerializer(data=data)
        if serializer.is_valid():
            serializer.save()
        else:
            print(index)
            print(serializer.errors)
