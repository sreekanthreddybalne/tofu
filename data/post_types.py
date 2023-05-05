from app.models import *
from api.serializers import *
import json

with open('data/post_types.json', 'r') as f:
    d = json.load(f)
    post_types = d["post_types"]
    PostType.objects.all().delete()
    for index, dt in enumerate(post_types):
        serializer = PostTypeCREATESerializer(data=dt)
        if serializer.is_valid():
            serializer.save()
        else:
            print(index)
            print(serializer.errors)
