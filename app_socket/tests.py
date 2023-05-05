from django.test import TestCase

from doclet.models import *
# Create your tests here.

a=User.objects.get(email='sreekanthreddytrnt@gmail.com')
#a.rooms.all()[0].send_message(message="Neeee",user=a)

room = Room.objects.get_or_create(title="testroom",user=a, user_id_list=[3], is_private=True)
print(room.id)
