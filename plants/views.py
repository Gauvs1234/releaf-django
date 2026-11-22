from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .filters import PlantFilter
from .forms import (
    ContactForm,
    MessageForm,
    PlantForm,
    ProfileForm,
    RegisterForm,
    ReviewForm,
)
from .models import (
    AdoptionRequest,
    Conversation,
    Favorite,
    Message,
    Plant,
    Profile,
    Review,
)
from .recommendations import (
    get_recommended_plants,
    has_recommendation_preferences,
)

def home(request):
    plant_filter = PlantFilter(request.GET, queryset=Plant.objects.all())
    featured_plants = (
        plant_filter.qs.filter(status="AVAILABLE")
        .select_related("owner")
        .order_by("-pk")[:3]
    )
    recent_reviews = (
        Review.objects.select_related("user", "plant")
        .order_by("-pk")[:3]
    )
    favorite_ids = set()
    recommendations = []
    recommendation_preferences_set = False
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorite.objects.filter(user=request.user).values_list("plant_id", flat=True)
        )
        recommendations = get_recommended_plants(request.user)
        profile = Profile.objects.filter(user=request.user).first()
        recommendation_preferences_set = has_recommendation_preferences(profile)
    return render(
        request,
        "home.html",
        {
            "plants": plant_filter.qs,
            "filter": plant_filter,
            "featured_plants": featured_plants,
            "recent_reviews": recent_reviews,
            "favorite_ids": favorite_ids,
            "recommendations": recommendations,
            "recommendation_preferences_set": recommendation_preferences_set,
        },
    )


def about(request):
    return render(
        request,
        "plants/about.html",
        {
            "plant_count": Plant.objects.count(),
            "member_count": get_user_model().objects.count(),
            "city_count": (
                Profile.objects.exclude(city="")
                .values("city")
                .distinct()
                .count()
            ),
            "available_count": Plant.objects.filter(status="AVAILABLE").count(),
        },
    )


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


def profile_detail(request, user_id):
    profile_user = get_object_or_404(get_user_model(), pk=user_id)
    profile, _ = Profile.objects.get_or_create(user=profile_user)
    plants = Plant.objects.filter(owner=profile_user).order_by("-pk")
    reviews = (
        Review.objects.filter(plant__owner=profile_user)
        .select_related("plant", "user")
        .order_by("-pk")
    )
    review_summary = reviews.aggregate(
        average=Avg("rating"),
        count=Count("pk"),
    )
    return render(
        request,
        "plants/profile_detail.html",
        {
            "profile": profile,
            "profile_user": profile_user,
            "plants": plants,
            "reviews": reviews,
            "review_summary": review_summary,
        },
    )


@login_required(login_url="login")
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile_detail", user_id=request.user.pk)
    else:
        form = ProfileForm(instance=profile)

    return render(request, "plants/profile_form.html", {"form": form})


@login_required(login_url="login")
def dashboard(request):
    my_plants = (
        Plant.objects.filter(owner=request.user)
        .annotate(review_count=Count("reviews"))
        .order_by("-pk")
    )
    reviews_received = (
        Review.objects.filter(plant__owner=request.user)
        .select_related("plant", "user")
        .order_by("-pk")
    )
    adoption_requests = (
        AdoptionRequest.objects.filter(plant__owner=request.user)
        .select_related("plant", "adopter")
        .order_by("-created_at", "-pk")
    )
    recent_messages = _recent_user_messages(request.user)
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "my_plants": my_plants,
            "reviews_received": reviews_received,
            "adoption_requests": adoption_requests,
            "recent_messages": recent_messages,
        },
    )


@login_required(login_url="login")
def adopter_dashboard(request):
    saved_plants = (
        Favorite.objects.filter(user=request.user)
        .select_related("plant", "plant__owner")
        .order_by("-created_at")
    )
    my_reviews = (
        Review.objects.filter(user=request.user)
        .select_related("plant", "plant__owner")
        .order_by("-pk")
    )
    my_adoption_requests = (
        AdoptionRequest.objects.filter(adopter=request.user)
        .select_related("plant", "plant__owner")
        .order_by("-created_at", "-pk")
    )
    recent_messages = _recent_user_messages(request.user)
    return render(
        request,
        "dashboard/adopter_dashboard.html",
        {
            "saved_plants": saved_plants,
            "my_reviews": my_reviews,
            "my_adoption_requests": my_adoption_requests,
            "recent_messages": recent_messages,
        },
    )


def _recent_user_messages(user):
    return (
        Message.objects.filter(Q(sender=user) | Q(receiver=user))
        .select_related("conversation__plant", "sender", "receiver")
        .order_by("-created_at", "-pk")[:5]
    )


@login_required(login_url="login")
@require_POST
@transaction.atomic
def request_adoption(request, pk):
    plant = get_object_or_404(
        Plant.objects.select_for_update(),
        pk=pk,
    )
    if plant.owner_id == request.user.pk:
        messages.error(request, "You cannot request to adopt your own plant.")
        return redirect("plant_detail", pk=plant.pk)
    if plant.status == "PENDING":
        pending_request = AdoptionRequest.objects.filter(
            plant=plant,
            status=AdoptionRequest.STATUS_PENDING,
        ).first()
        if pending_request and pending_request.adopter_id == request.user.pk:
            messages.info(request, "Your adoption request is already pending.")
        elif pending_request:
            messages.info(request, "An adoption request is already being reviewed.")
        else:
            messages.error(request, "This plant is not currently available for adoption.")
        return redirect("plant_detail", pk=plant.pk)
    if plant.status != "AVAILABLE":
        messages.error(request, "This plant is not currently available for adoption.")
        return redirect("plant_detail", pk=plant.pk)

    adoption_request, created = AdoptionRequest.objects.get_or_create(
        plant=plant,
        status=AdoptionRequest.STATUS_PENDING,
        defaults={"adopter": request.user},
    )
    if not created:
        if adoption_request.adopter_id == request.user.pk:
            messages.info(request, "Your adoption request is already pending.")
        else:
            messages.info(request, "An adoption request is already being reviewed.")
        return redirect("plant_detail", pk=plant.pk)

    plant.status = "PENDING"
    plant.save(update_fields=["status"])
    messages.success(request, "Your adoption request has been sent to the owner.")
    return redirect("plant_detail", pk=plant.pk)


@login_required(login_url="login")
@require_POST
@transaction.atomic
def accept_adoption(request, request_id):
    adoption_request = get_object_or_404(
        AdoptionRequest.objects.select_for_update().select_related("plant"),
        pk=request_id,
        plant__owner=request.user,
    )
    plant = adoption_request.plant
    if (
        adoption_request.status != AdoptionRequest.STATUS_PENDING
        or plant.status != "PENDING"
    ):
        messages.error(request, "This adoption request is no longer pending.")
        return redirect("dashboard")

    adoption_request.status = AdoptionRequest.STATUS_ACCEPTED
    adoption_request.save(update_fields=["status"])
    plant.status = "ADOPTED"
    plant.adopted_by = adoption_request.adopter
    plant.save(update_fields=["status", "adopted_by"])
    messages.success(request, f"You accepted the request for {plant.name}.")
    return redirect("dashboard")


@login_required(login_url="login")
@require_POST
@transaction.atomic
def reject_adoption(request, request_id):
    adoption_request = get_object_or_404(
        AdoptionRequest.objects.select_for_update().select_related("plant"),
        pk=request_id,
        plant__owner=request.user,
    )
    plant = adoption_request.plant
    if (
        adoption_request.status != AdoptionRequest.STATUS_PENDING
        or plant.status != "PENDING"
    ):
        messages.error(request, "This adoption request is no longer pending.")
        return redirect("dashboard")

    adoption_request.status = AdoptionRequest.STATUS_REJECTED
    adoption_request.save(update_fields=["status"])
    plant.status = "AVAILABLE"
    plant.adopted_by = None
    plant.save(update_fields=["status", "adopted_by"])
    messages.success(request, f"You rejected the request for {plant.name}.")
    return redirect("dashboard")


def plant_detail(request, pk):
    plant = get_object_or_404(
        Plant.objects.select_related("owner"),
        pk=pk,
    )
    Profile.objects.get_or_create(user=plant.owner)
    is_favorite = (
        request.user.is_authenticated
        and Favorite.objects.filter(user=request.user, plant=plant).exists()
    )
    my_adoption_request = None
    if request.user.is_authenticated:
        my_adoption_request = (
            AdoptionRequest.objects.filter(plant=plant, adopter=request.user)
            .order_by("-created_at", "-pk")
            .first()
        )
    reviews = (
        Review.objects.filter(plant=plant)
        .select_related("user")
        .order_by("-pk")
    )
    has_reviewed = (
        request.user.is_authenticated
        and Review.objects.filter(plant=plant, user=request.user).exists()
    )
    can_review = (
        request.user.is_authenticated
        and plant.status == "ADOPTED"
        and plant.adopted_by_id == request.user.pk
        and plant.owner_id != request.user.pk
        and not has_reviewed
    )
    return render(
        request,
        "plants/plant_detail.html",
        {
            "plant": plant,
            "is_favorite": is_favorite,
            "my_adoption_request": my_adoption_request,
            "reviews": reviews,
            "has_reviewed": has_reviewed,
            "can_review": can_review,
            "review_form": ReviewForm() if can_review else None,
        },
    )


@login_required(login_url="login")
@require_POST
def leave_review(request, pk):
    plant = get_object_or_404(Plant, pk=pk)
    if (
        plant.status != "ADOPTED"
        or plant.adopted_by_id != request.user.pk
        or plant.owner_id == request.user.pk
    ):
        messages.error(request, "Only the recorded adopter can review this plant.")
        return redirect("plant_detail", pk=plant.pk)

    if Review.objects.filter(plant=plant, user=request.user).exists():
        messages.info(request, "You have already reviewed this adoption.")
        return redirect("plant_detail", pk=plant.pk)

    form = ReviewForm(request.POST)
    if form.is_valid():
        review, created = Review.objects.get_or_create(
            plant=plant,
            user=request.user,
            defaults={
                "rating": form.cleaned_data["rating"],
                "comment": form.cleaned_data["comment"],
            },
        )
        if created:
            messages.success(request, "Thank you for sharing your review.")
        else:
            messages.info(request, "You have already reviewed this adoption.")
    else:
        messages.error(request, "Please provide a valid rating and review.")
    return redirect("plant_detail", pk=plant.pk)


@login_required(login_url="login")
def favorites(request):
    saved_plants = (
        Favorite.objects.filter(user=request.user)
        .select_related("plant", "plant__owner")
        .order_by("-created_at")
    )
    return render(
        request,
        "plants/favorites.html",
        {"saved_plants": saved_plants},
    )


@login_required(login_url="login")
@require_POST
def toggle_favorite(request, pk):
    plant = get_object_or_404(Plant, pk=pk)
    if plant.owner_id == request.user.pk:
        messages.error(request, "You cannot save your own plant listing.")
    else:
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            plant=plant,
        )
        if created:
            messages.success(request, "Plant saved to your favorites.")
        else:
            favorite.delete()
            messages.success(request, "Plant removed from your favorites.")

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("plant_detail", pk=plant.pk)


@login_required(login_url="login")
def message_inbox(request):
    folder = request.GET.get("folder")
    if folder not in {"inbox", "sent"}:
        folder = "inbox"
    participant_field = "sender" if folder == "sent" else "receiver"
    matching_messages = Message.objects.filter(
        **{f"{participant_field}_id": request.user.pk}
    )
    latest_messages = matching_messages.filter(
        conversation_id=OuterRef("pk")
    ).order_by("-created_at", "-pk")
    conversations = (
        Conversation.objects.filter(pk__in=matching_messages.values("conversation_id"))
        .select_related("participant_one", "participant_two", "plant")
        .annotate(
            latest_text=Subquery(latest_messages.values("text")[:1]),
            latest_sender_id=Subquery(latest_messages.values("sender_id")[:1]),
            latest_created_at=Subquery(latest_messages.values("created_at")[:1]),
            unread_count=Count(
                "messages",
                filter=Q(
                    messages__receiver=request.user,
                    messages__is_read=False,
                ),
            ),
        )
        .order_by("-updated_at", "-pk")
    )
    return render(
        request,
        "plants/message_inbox.html",
        {"conversations": conversations, "folder": folder},
    )


@login_required(login_url="login")
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.filter(
            participant_one=request.user,
        )
        | Conversation.objects.filter(
            participant_two=request.user,
        ),
        pk=conversation_id,
    )
    if request.method == "GET":
        conversation.messages.filter(
            receiver=request.user,
            is_read=False,
        ).update(is_read=True)

    if conversation.participant_one_id == request.user.pk:
        recipient = conversation.participant_two
    else:
        recipient = conversation.participant_one

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=recipient,
                text=form.cleaned_data["text"],
            )
            conversation.save(update_fields=["updated_at"])
            messages.success(request, "Your message has been sent.")
            return redirect("conversation_detail", conversation_id=conversation.pk)
    else:
        form = MessageForm()

    conversation_messages = conversation.messages.select_related("sender").order_by(
        "created_at",
        "pk",
    )
    return render(
        request,
        "plants/conversation_detail.html",
        {
            "conversation": conversation,
            "conversation_messages": conversation_messages,
            "recipient": recipient,
            "form": form,
        },
    )


@login_required(login_url="login")
def contact_owner(request, pk):
    plant = get_object_or_404(Plant.objects.select_related("owner"), pk=pk)
    if plant.owner_id == request.user.pk:
        messages.error(request, "You cannot contact yourself about your own listing.")
        return redirect("plant_detail", pk=plant.pk)

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            participant_one, participant_two = sorted(
                (request.user, plant.owner),
                key=lambda participant: participant.pk,
            )
            conversation, _ = Conversation.objects.get_or_create(
                participant_one=participant_one,
                participant_two=participant_two,
                plant=plant,
            )
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=plant.owner,
                text=form.cleaned_data["text"],
            )
            conversation.save(update_fields=["updated_at"])
            messages.success(request, "Your message has been sent to the plant owner.")
            return redirect("plant_detail", pk=plant.pk)
    else:
        form = MessageForm()

    return render(
        request,
        "plants/contact_owner.html",
        {"form": form, "plant": plant},
    )


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


@login_required(login_url="login")
def edit_plant(request, pk):
    plant = get_object_or_404(Plant, pk=pk, owner=request.user)
    if request.method == "POST":
        form = PlantForm(request.POST, request.FILES, instance=plant)
        if form.is_valid():
            form.save()
            messages.success(request, "Your plant listing has been updated.")
            return redirect("dashboard")
    else:
        form = PlantForm(instance=plant)

    return render(
        request,
        "plants/edit_plant.html",
        {"form": form, "plant": plant},
    )


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            return redirect("home")
    else:
        form = RegisterForm()

    return render(
        request,
        "plants/register.html",
        {"form": form},
    )