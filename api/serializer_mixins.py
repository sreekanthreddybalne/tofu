



class ConditionalRequiredPerFieldMixin:
"""Allows to use serializer methods to allow change field is required or not"""

def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    for field_name, field in self.fields.items():
        method_name = f'is_{field_name}_required'
        if hasattr(self, method_name):
            field.required = getattr(self, method_name)()


#Usage
class MySerializer(ConditionalRequiredPerFieldMixin, serializers.ModelSerializer):
    subject_id = serializers.CharField(max_length=128, min_length=3, required=False)

    def is_subject_id_required(self):
        study = self.context['study']
        return not study.is_community_study



class ActionRequiredFieldsMixin:
    """Required fields per DRF action
    Example:
    PER_ACTION_REQUIRED_FIELDS = {
        'update': ['notes']
    }
    """
    PER_ACTION_REQUIRED_FIELDS = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context.get('view'):
            action = self.context['view'].action
            required_fields = (self.PER_ACTION_REQUIRED_FIELDS or {}).get(action)
            if required_fields:
                for field_name in required_fields:
                    self.fields[field_name].required = True
