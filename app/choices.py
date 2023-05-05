from django.utils.translation import gettext as _

GENDER_MALE ="male"
GENDER_FEMALE = "female"
GENDER_OTHER = "other"


GENDER = (
    (GENDER_MALE, _("male")),
    (GENDER_FEMALE, _("female")),
    (GENDER_OTHER, _("other"))
)


SUPER_ADMIN =1
