import django_filters

from .models import Plant


class PlantFilter(django_filters.FilterSet):
    species = django_filters.CharFilter(
        field_name="species",
        lookup_expr="icontains",
        label="Species",
    )
    location = django_filters.CharFilter(
        field_name="location",
        lookup_expr="icontains",
        label="Location",
    )
    care_level = django_filters.ChoiceFilter(
        choices=Plant.CARE_LEVELS,
        label="Care level",
    )
    size = django_filters.ChoiceFilter(
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        method="filter_size",
        label="Size",
    )
    environment = django_filters.ChoiceFilter(
        choices=Plant.ENVIRONMENT_CHOICES,
        label="Environment",
    )

    def filter_size(self, queryset, name, value):
        return queryset.filter(size__iexact=value)

    class Meta:
        model = Plant
        fields = [
            "species",
            "location",
            "care_level",
            "size",
            "environment",
        ]
