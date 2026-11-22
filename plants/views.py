from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from .filters import PlantFilter
from .forms import ContactForm, PlantForm, RegisterForm
from .models import Plant

def home(request):
    plant_filter = PlantFilter(request.GET, queryset=Plant.objects.all())
    return render(
        request,
        "home.html",
        {
            "plants": plant_filter.qs,
            "filter": plant_filter,
        },
    )


def about(request):
    return render(request, "plants/about.html")


def services(request):
    return render(request, "plants/services.html")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks for reaching out. Your message has been received.")
            return redirect("contact")
    else:
        form = ContactForm()

    return render(request, "plants/contact.html", {"form": form})


@login_required(login_url="login")
def create_plant(request):

    if request.method == "POST":
        form = PlantForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            plant = form.save(commit=False)
            plant.owner = request.user
            plant.save()
            return redirect("home")

    else:
        form = PlantForm()

    return render(
        request,
        "plants/create_plant.html",
        {"form": form}
    )


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = RegisterForm()

    return render(
        request,
        "plants/register.html",
        {"form": form},
    )