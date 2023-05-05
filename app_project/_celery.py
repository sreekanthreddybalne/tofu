import os
from celery import Celery
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_project.settings')
os.environ.setdefault("SEO_JS_PRERENDER_TOKEN", "RMVQxJkVVugDjcPgHakN")
#os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1') #this added for an error on windows machine
app = Celery('app_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
