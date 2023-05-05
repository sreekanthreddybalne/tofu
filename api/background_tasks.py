from __future__ import absolute_import, unicode_literals
from .smser import *
from celery import shared_task




@shared_task
def task_send_activation_mail(user_id):
    pass#return send_activation_mail(user_id)

@shared_task
def task_send_welcome_mail(user_id):
    pass#return send_welcome_mail(user_id)

@shared_task
def task_send_confirmation_mail(user_id):
    pass#return send_confirmation_mail(user_id)

@shared_task
def task_send_otp_sms(phone_number, code):
	message = code+" is your OTP for Tofu. Please do not share your OTP with anyone. https://tofuapp.tech"
	return sendSMS(phone_number, message)
