from app.models import *
from api.serializers import *
from django.db import transaction

@transaction.atomic
def clean_db():
    User.objects.exclude(phone_number="AnonymousUser").delete()
    Post.objects.all().delete()
    UserLocation.objects.all().delete()
    OTP.objects.all().delete()
    DishFile.objects.all().delete()
    RestaurantFile.objects.all().delete()
    Feedback.objects.all().delete()
    TokenBlackList.objects.all().delete()
    Activity.objects.all().delete()
    PostComment.objects.all().delete()
    DishCollection.objects.all().delete()

if __name__ == '__main__':
    clean_db()
    print("db cleaned")
