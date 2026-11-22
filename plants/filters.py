import django_filters

from .models import Plant


class PlantFilter(django_filters.FilterSet):
    class Meta:
        model = Plant
        fields = [
            "species",
            "location",
            "care_level",
        ]
