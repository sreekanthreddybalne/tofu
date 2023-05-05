from django.db import models
import re

class FK(models.ForeignKey):
    def contribute_to_class(self, cls, name, private_only=False, **kwargs):
        super().contribute_to_class(cls, name, private_only=False, **kwargs)
        self.remote_field.related_name = ("_".join(re.findall('[A-Z][^A-Z]*', cls.__name__))+"s").lower()

class IntegerRangeField(models.IntegerField):
    def __init__(self, verbose_name=None, name=None, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        models.IntegerField.__init__(self, verbose_name, name, **kwargs)
    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value':self.max_value}
        defaults.update(kwargs)
        return super().formfield(**defaults)
