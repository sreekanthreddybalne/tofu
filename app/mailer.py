from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import get_template
from django.template.loader import render_to_string
from .tokens import account_activation_token
from .settings import *

def send_activation_mail(user_id):
    from app.models import User
    user = User.objects.get(pk=user_id)
    if not user.email: return
    subject = COMPANY_FULL_NAME+' | Confirm Your Email'
    message = get_template('mailers/activation_mail.html').render({
        'domain_url': DOMAIN_URL,
        'domain': DOMAIN,
        'company_short_name': COMPANY_SHORT_NAME,
        'domain_short_name': DOMAIN_SHORT_NAME,
        'domain_full_name': DOMAIN_FULL_NAME,
        'logo': LOGO,
        'domain_email': DOMAIN_EMAIL,
        'domain_support_email': DOMAIN_SUPPORT_EMAIL,
        'domain_support_url': DOMAIN_SUPPORT_URL,
        'mobile_support': MOBILE_SUPPORT,
        'user': user,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)).decode(),
        'token': account_activation_token.make_token(user),
    })
    user.email_user(subject, '', from_email=DOMAIN_FULL_NAME +' <'+DOMAIN_EMAIL+'>', html_message=message)
    return user.email

def send_welcome_mail(user_id):
    from app.models import User
    user = User.objects.get(pk=user_id)
    if not user.email: return
    subject = COMPANY_SHORT_NAME+' | Welcome Message from CEO'
    message = get_template('mailers/welcome_mail.html').render({
        'domain_url': DOMAIN_URL,
        'domain': DOMAIN,
        'company_short_name': COMPANY_SHORT_NAME,
        'domain_short_name': DOMAIN_SHORT_NAME,
        'domain_full_name': DOMAIN_FULL_NAME,
        'logo': LOGO,
        'domain_email': DOMAIN_EMAIL,
        'domain_support_email': DOMAIN_SUPPORT_EMAIL,
        'domain_support_url': DOMAIN_SUPPORT_URL,
        'mobile_support': MOBILE_SUPPORT,
        'user': user,
        'ceo': CEO,
    })
    user.email_user(subject, '', from_email=DOMAIN_FULL_NAME +' <'+CEO["email"]+'>', html_message=message)
    return user.email

def send_confirmation_mail(user_id):
    from app.models import User
    user = User.objects.get(pk=user_id)
    if not user.email: return
    subject = COMPANY_FULL_NAME+' | Confirm Your Email'
    message = get_template('mailers/confirmation_mail.html').render({
        'domain_url': DOMAIN_URL,
        'domain': DOMAIN,
        'company_short_name': COMPANY_SHORT_NAME,
        'domain_short_name': DOMAIN_SHORT_NAME,
        'domain_full_name': DOMAIN_FULL_NAME,
        'logo': LOGO,
        'domain_email': DOMAIN_EMAIL,
        'domain_support_email': DOMAIN_SUPPORT_EMAIL,
        'domain_support_url': DOMAIN_SUPPORT_URL,
        'mobile_support': MOBILE_SUPPORT,
        'user': user,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)).decode(),
        'token': account_activation_token.make_token(user),
    })
    user.email_user(subject, '', from_email=DOMAIN_FULL_NAME +' <'+DOMAIN_EMAIL+'>', html_message=message)
    return user.email

def send_transaction_mail(transaction_id):
    from app.models import Transaction
    print(transaction_id)
    transaction = Transaction.objects.get(pk=transaction_id)
    user = transaction.user
    if not user.email: return
    subject = 'Your '+COMPANY_SHORT_NAME+' #'+str(transaction.id)+' Order Reference'
    message = get_template('mailers/transaction_mail.html').render({
        'domain_url': DOMAIN_URL,
        'domain': DOMAIN,
        'company_short_name': COMPANY_SHORT_NAME,
        'domain_short_name': DOMAIN_SHORT_NAME,
        'domain_full_name': DOMAIN_FULL_NAME,
        'logo': LOGO,
        'domain_email': DOMAIN_EMAIL,
        'domain_support_email': DOMAIN_SUPPORT_EMAIL,
        'domain_support_url': DOMAIN_SUPPORT_URL,
        'mobile_support': MOBILE_SUPPORT,
        'user': user,
        'transaction':transaction,
    })
    user.email_user(subject, '', from_email=DOMAIN_FULL_NAME +' <'+PAYMENTS_EMAIL+'>', html_message=message)
    return user.email
