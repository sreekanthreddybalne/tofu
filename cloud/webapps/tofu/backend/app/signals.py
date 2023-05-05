import itertools
from django.conf import settings
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm
from app_socket.utils import broadcast_data, get_user_room, broadcast_notification
from api.serializers import *
import app.choices as choices
from .models import *
from .utils import generate_room_code
from .tasks import action_after_new_user_save, action_after_new_prospect_save
from .choices import *
from asgiref.sync import async_to_sync
from django.contrib.contenttypes.models import ContentType
from app import choices

post_content_type = ContentType.objects.get_for_model(Post)
post_comment_content_type = ContentType.objects.get_for_model(PostComment)

def get_content_type(instance):
    return ContentType.objects.get_for_model(instance.__class__)

# @receiver(post_save, sender=User)
# def after_user_save(sender, instance, created, **kwargs):
#     if created:
#         transaction.on_commit(action_after_new_user_save.s(instance.pk).delay)
#
# # connect all subclasses of base content item too
# for subclass in User.__subclasses__():
#     post_save.connect(after_user_save, subclass)

@receiver(post_save, sender=PostComment)
def after_post_comment_save(sender, instance, created, **kwargs):
    post = instance.post
    post.showcase_comment=instance
    post.save()

@receiver(post_save, sender=Activity)
def after_activity_save(sender, instance, created, **kwargs):
    if instance.content_type==post_comment_content_type:
        if instance.activity_type==Activity.UP_VOTE:
            post_comment = PostComment.objects.get(pk=instance.object_id)
            post_comment.upvotes_count+=1
            post_comment.save()
    elif instance.content_type==post_content_type:
        if instance.activity_type==Activity.UP_VOTE:
            post = Post.objects.get(pk=instance.object_id)
            post.upvotes_count+=1
            post.save()

@receiver(pre_delete, sender=Activity)
def before_activity_delete(sender, instance, **kwargs):
    if instance.content_type==post_comment_content_type:
        if instance.activity_type==Activity.UP_VOTE:
            post_comment = PostComment.objects.get(pk=instance.object_id)
            post_comment.upvotes_count-=1
            post_comment.save()
    elif instance.content_type==post_content_type:
        if instance.activity_type==Activity.UP_VOTE:
            post = Post.objects.get(pk=instance.object_id)
            post.upvotes_count-=1
            post.save()
