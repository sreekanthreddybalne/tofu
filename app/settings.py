from django.conf import settings


DOMAIN_SHORT_NAME = 'cognerium'
DOMAIN_FULL_NAME = 'Cognerium Research Labs India'
DOMAIN = DOMAIN_SHORT_NAME+'.com'
SECURE = True
DOMAIN_URL = ('https' if SECURE else 'http') + '://'+DOMAIN
COMPANY_FULL_NAME = 'Cognerium Research Labs India Pvt Ltd'
COMPANY_SHORT_NAME = 'cognerium'
LOGO = "https://i.imgur.com/RqNSLyZ.png"
DOMAIN_EMAIL = 'admin@'+DOMAIN
DOMAIN_SUPPORT_EMAIL = 'support@'+DOMAIN
DOMAIN_SUPPORT_URL = DOMAIN_URL+'/company/support/'
PRESS_EMAIL = 'press@'+DOMAIN
CAREERS_EMAIL = 'careers@'+DOMAIN
PAYMENTS_EMAIL = 'payments@'+DOMAIN
PRESS_EMAIL = 'press@'+DOMAIN
WELCOME_EMAIL = 'welcome@'+DOMAIN
ADMIN_EMAIL = 'admin@'+DOMAIN
MOBILE_SUPPORT='+91 88888 88888'

CEO = {
    "name": "",
    "email": "admin@"+DOMAIN,
    "mobile": "+91 888888888888"
}

PHONE_REGEX = r'^[6789]\d{9}$'
ROOM_CODE_LENGTH = 10
CAMPAIGN_TASK_BATCH_CODE_LENGTH = 8
USERNAME_MIN_LENGTH = 5
USERNAME_MAX_LENGTH = 12
CODE_LENGTH = 8
PASSWORD_MIN_LENGTH=6
OTP_LENGTH = 4
OTP_EXPIRY = 15*60 #15 minutes
OTP_TRIES=3


NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS = getattr(settings, 'NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS', True)

MSG_TYPE_MESSAGE = 0  # For standard messages
MSG_TYPE_WARNING = 1  # For yellow messages
MSG_TYPE_ALERT = 2  # For red & dangerous alerts
MSG_TYPE_MUTED = 3  # For just OK information that doesn't bother users
MSG_TYPE_ENTER = 4  # For just OK information that doesn't bother users
MSG_TYPE_LEAVE = 5  # For just OK information that doesn't bother users

MESSAGE_TYPES_CHOICES = getattr(settings, 'MESSAGE_TYPES_CHOICES', (
    (MSG_TYPE_MESSAGE, 'MESSAGE'),
    (MSG_TYPE_WARNING, 'WARNING'),
    (MSG_TYPE_ALERT, 'ALERT'),
    (MSG_TYPE_MUTED, 'MUTED'),
    (MSG_TYPE_ENTER, 'ENTER'),
    (MSG_TYPE_LEAVE, 'LEAVE')))

MESSAGE_TYPES_LIST = getattr(settings, 'MESSAGE_TYPES_LIST',
                             [MSG_TYPE_MESSAGE,
                              MSG_TYPE_WARNING,
                              MSG_TYPE_ALERT,
                              MSG_TYPE_MUTED,
                              MSG_TYPE_ENTER,
                              MSG_TYPE_LEAVE])
