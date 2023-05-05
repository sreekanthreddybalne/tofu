from app.models import (DataStore, Dish)
from django.db.models import Subquery, OuterRef, F, Count, Max, When, Case, IntegerField, FloatField, ExpressionWrapper
# def run_global_feed_settings():
#

def generate_dish_score():

    ds, created = DataStore.objects.get_or_create(pk=1)

    q = Dish.objects.exclude(
        zomato_number_of_ratings=None
    ).aggregate(Max('zomato_number_of_ratings'))
    zomato_number_of_ratings__max = q["zomato_number_of_ratings__max"]
    q = Dish.objects.annotate(
        tofu_number_of_ratings=Count('posts')
    ).aggregate(Max('tofu_number_of_ratings'))
    tofu_number_of_ratings__max = q["tofu_number_of_ratings__max"]
    q = Dish.objects.exclude(posts=None).annotate(
        files_count=Count(Case(When(posts__post_files=None, then=0), default='posts__post_files', output_field=IntegerField()))
    ).aggregate(Max('files_count'))
    files_count__max = q["files_count__max"]


    Dish.objects.filter(zomato_number_of_ratings__gte=ds.zomato_number_of_ratings_threshold).update(
        score=Subquery(
            Dish.objects.filter(
                id=OuterRef('id')
            ).annotate(
                tofu_rating_=Case(
                    When(rating=None, then=ds.new_dish_rating),
                    When(rating=0, then=ds.new_dish_rating),
                    default=F('rating'), output_field=FloatField()
                ),
                tofu_number_of_ratings_ = Count('posts', output_field=FloatField()),
                zomato_rating_=Case(
                    When(zomato_rating=None, then=ds.new_dish_rating),
                    When(zomato_rating=0, then=ds.new_dish_rating),
                    default=F('zomato_rating'), output_field=FloatField()
                ),
                zomato_number_of_ratings_ = Case(
                    When(zomato_number_of_ratings=None, then=0), default=F('zomato_number_of_ratings'), output_field=FloatField()
                ),
                files_count = Count('files', output_field=FloatField()),
                score_ = (F('tofu_rating_')/5)*ds.weightage_tofu_rating +
                (F('tofu_number_of_ratings_')/tofu_number_of_ratings__max)*ds.weightage_tofu_number_of_ratings +
                (F('zomato_rating_')/5)*ds.weightage_zomato_rating +
                (F('zomato_number_of_ratings_')/zomato_number_of_ratings__max)*ds.weightage_zomato_number_of_ratings +
                (F('files_count')*ds.weightage_files/files_count__max)
            ).values('score_')[:1]
        )
    )
