from rest_framework import filters, serializers
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
import re
import ast

not_regex = "__not$"
in_regex = "__in$"
class CustomFilterBackend(DjangoFilterBackend):
    """
    Custom Filter on objects to enable `exclude`, `__in`.
    """
    def filter_queryset(self, request, queryset, view):
        for param in request.query_params.keys():
            if request.query_params.get(param):
                if re.search(not_regex, param):
                    field = re.sub(not_regex, '', param)
                    if field in view.filter_fields:
                        d = {field: request.query_params.get(param)}
                        queryset = queryset.exclude(**d)
                if re.search(in_regex, param):
                    field = re.sub(in_regex, '', param)
                    if field in view.filter_fields:
                        ls=''
                        try:
                            ls = ast.literal_eval(request.query_params.get(param))
                            if not type(ls)==list: ls=''
                        except:
                            raise serializers.ValidationError("Expected a list of "+field+"s")
                        d = {param: ls}
                        queryset = queryset.filter(**d)

        return super().filter_queryset(request, queryset, view)

class IsOwnerFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(owner=request.user)

class MessageFilterBackend(DjangoFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """
    def filter_queryset(self, request, queryset, view):
        code = request.query_params.get('code')
        if code:
            if code.isnumeric():
                return queryset.filter(chat_group__pk=code)
            return queryset.filter(Q(receiver__code=code) | Q(sender__code=code))
        return super().filter_queryset(request, queryset, view)

class ProspectFilterBackend(CustomFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """
    def filter_queryset(self, request, queryset, view):
        status = request.query_params.get('status')
        status__not = request.query_params.get('status__not')
        if status:
            statuses = status.split("||")
            pks = [p.pk for p in queryset.all() if p.status in statuses]
            queryset= queryset.filter(pk__in=pks)
        if status__not:
            pks = [p.pk for p in queryset.all() if p.status!=status__not]
            queryset= queryset.filter(pk__in=pks)
        return super().filter_queryset(request, queryset, view)

class CustomSearchFilter(filters.SearchFilter):

    def get_search_fields(self, view, request):
        only = request.query_params.get('only')
        if only and hasattr(view, 'search_fields') and only in view.search_fields:
            return (only,)
        return super(CustomSearchFilter, self).get_search_fields(view, request)
