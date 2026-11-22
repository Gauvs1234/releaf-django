from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import ContactMessage, Plant, Profile, Review


class PlantForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Description",
    )
    size = forms.CharField(max_length=50, label="Size")
    sunlight_requirements = forms.CharField(
        max_length=100,
        label="Sunlight requirements",
    )
    watering_frequency = forms.CharField(
        max_length=100,
        label="Watering frequency",
    )
    environment = forms.ChoiceField(
        choices=Plant.ENVIRONMENT_CHOICES,
        label="Growing environment",
    )

    class Meta:
        model = Plant
        fields = [
            "name",
            "species",
            "age",
            "description",
            "care_tips",
            "care_level",
            "size",
            "sunlight_requirements",
            "watering_frequency",
            "environment",
            "location",
            "image",
        ]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "city",
            "bio",
            "preferred_care_level",
            "preferred_size",
            "preferred_environment",
            "sunlight_preference",
            "image",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "city": "Location preference (city)",
            "preferred_care_level": "Preferred care level",
            "preferred_size": "Preferred plant size",
            "preferred_environment": "Preferred environment",
            "sunlight_preference": "Sunlight preference",
        }


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(rating, f"{rating} star{'s' if rating != 1 else ''}") for rating in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
        }


class MessageForm(forms.Form):
    text = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={"rows": 5}),
    )


class RegisterForm(UserCreationForm):
    pass


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "message"]
        labels = {
            "name": "Full name",
            "email": "Email",
            "phone": "Phone number",
            "message": "Message",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone number"}),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "How can we help?",
                }
            ),
        }