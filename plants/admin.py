from django.contrib import admin
from .models import AdoptionRequest, ContactMessage, Plant, Profile


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "species",
        "owner",
        "status",
        "adopted_by",
        "care_level",
        "location",
    )
    list_filter = ("status", "care_level", "location")
    search_fields = ("name", "species", "location", "owner__username")
    readonly_fields = ("status", "adopted_by")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "city")
    search_fields = ("user__username", "city", "bio")


@admin.register(AdoptionRequest)
class AdoptionRequestAdmin(admin.ModelAdmin):
    list_display = ("plant", "adopter", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("plant__name", "adopter__username")
    readonly_fields = ("plant", "adopter", "status", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "submitted_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("submitted_at",)
