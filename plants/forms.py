from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import ContactMessage, Plant


class PlantForm(forms.ModelForm):
    class Meta:
        model = Plant
        fields = [
            "name",
            "species",
            "age",
            "care_tips",
            "care_level",
            "location",
            "image",
        ]


class RegisterForm(UserCreationForm):
    pass


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }