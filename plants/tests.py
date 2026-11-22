from io import BytesIO

from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import (
    AdoptionRequest,
    ContactMessage,
    Conversation,
    Favorite,
    Message,
    Plant,
    Profile,
    Review,
)
from .forms import PlantForm, ProfileForm, ReviewForm
from .recommendations import calculate_match, score_plant_match


class HomeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="plant-owner",
            password="StrongTestPassword123!",
        )

    def test_home_lists_plants(self):
        Plant.objects.create(
            name="Snake Plant",
            species="Dracaena trifasciata",
            age=2,
            care_tips="Water sparingly.",
            care_level="easy",
            size="Medium",
            environment="indoor",
            sunlight_requirements="Indirect sunlight",
            watering_frequency="Twice per week",
            location="Living room",
            image="plants/snake-plant.jpg",
            owner=self.user,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Snake Plant")
        self.assertContains(response, "Dracaena trifasciata")
        self.assertContains(response, "Living room")
        self.assertContains(response, "Medium")
        self.assertContains(response, "Indirect sunlight")
        self.assertContains(response, "Twice per week")
        self.assertContains(response, "Available")
        self.assertQuerySetEqual(
            response.context["plants"],
            [Plant.objects.get(name="Snake Plant")],
        )

    def test_home_filters_by_partial_species_location_care_size_and_environment(self):
        Plant.objects.create(
            name="Snake Plant",
            species="Dracaena trifasciata",
            age=2,
            care_tips="Water sparingly.",
            care_level="easy",
            size="Medium",
            environment="indoor",
            location="Living room",
            image="plants/snake-plant.jpg",
            owner=self.user,
        )
        Plant.objects.create(
            name="Fern",
            species="Nephrolepis exaltata",
            age=1,
            care_tips="Keep moist.",
            care_level="difficult",
            size="Small",
            environment="outdoor",
            location="Bathroom",
            image="plants/fern.jpg",
            owner=self.user,
        )

        response = self.client.get(
            reverse("home"),
            {
                "species": "dracaena",
                "location": "living",
                "care_level": "easy",
                "size": "medium",
                "environment": "indoor",
            },
        )

        self.assertContains(response, "Snake Plant")
        self.assertNotContains(response, "Fern")


class RecommendationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.adopter = user_model.objects.create_user(
            username="match-adopter",
            password="StrongTestPassword123!",
        )
        self.owner = user_model.objects.create_user(
            username="match-owner",
            password="StrongTestPassword123!",
        )
        self.profile = Profile.objects.create(
            user=self.adopter,
            city="Chandigarh",
            preferred_care_level="easy",
            preferred_size="Medium",
            preferred_environment="indoor",
            sunlight_preference="Low sunlight",
        )

    def create_plant(self, owner, name, **overrides):
        plant_data = {
            "name": name,
            "species": "Dracaena trifasciata",
            "age": 2,
            "care_tips": "Water sparingly.",
            "care_level": "easy",
            "size": "Medium",
            "status": "AVAILABLE",
            "environment": "indoor",
            "sunlight_requirements": "Low sunlight",
            "location": "Chandigarh, Sector 17",
            "image": f"plants/{name.lower().replace(' ', '-')}.jpg",
            "owner": owner,
        }
        plant_data.update(overrides)
        return Plant.objects.create(**plant_data)

    def test_scoring_awards_points_for_each_matching_preference(self):
        plant = self.create_plant(self.owner, "Snake Plant")

        self.assertEqual(score_plant_match(plant, self.profile), 140)

        plant.environment = "both"
        plant.location = "Mohali"
        plant.sunlight_requirements = "Bright direct sunlight"
        plant.size = "Small"
        self.assertEqual(score_plant_match(plant, self.profile), 65)

    def test_core_match_weights_are_care_40_location_30_and_size_20(self):
        self.profile.preferred_environment = ""
        self.profile.sunlight_preference = ""
        plant = self.create_plant(self.owner, "Core Match")

        self.assertEqual(calculate_match(plant, self.profile), 90)

        plant.size = "Small"
        self.assertEqual(calculate_match(plant, self.profile), 70)

        plant.location = "Delhi"
        self.assertEqual(calculate_match(plant, self.profile), 40)

        plant.care_level = "moderate"
        self.assertEqual(calculate_match(plant, self.profile), 0)

    def test_home_ranks_available_matches_and_excludes_own_listings(self):
        perfect_match = self.create_plant(self.owner, "Perfect Match")
        care_match = self.create_plant(
            self.owner,
            "Care Match",
            environment="outdoor",
            sunlight_requirements="Direct sunlight",
            location="Delhi",
            size="Small",
        )
        self.create_plant(
            self.owner,
            "Unavailable Match",
            status="PENDING",
        )
        self.create_plant(self.adopter, "Own Match")

        self.client.force_login(self.adopter)
        response = self.client.get(reverse("home"))

        recommendations = response.context["recommendations"]
        self.assertEqual(
            [item["plant"] for item in recommendations],
            [perfect_match, care_match],
        )
        self.assertEqual([item["score"] for item in recommendations], [140, 40])
        self.assertTrue(response.context["recommendation_preferences_set"])
        self.assertContains(response, "Recommended Plants")

    def test_recommendation_section_prompts_for_preferences_when_not_set(self):
        Profile.objects.filter(user=self.adopter).update(
            city="",
            preferred_care_level="",
            preferred_size="",
            preferred_environment="",
            sunlight_preference="",
        )
        self.client.force_login(self.adopter)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Add your location and plant preferences")
        self.assertFalse(response.context["recommendation_preferences_set"])


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="existing-user",
            password="StrongTestPassword123!",
        )

    def test_registration_creates_user_and_redirects_home(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "password1": "StrongTestPassword123!",
                "password2": "StrongTestPassword123!",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(get_user_model().objects.filter(username="newuser").exists())
        self.assertEqual(response.wsgi_request.user.username, "newuser")
        self.assertTrue(Profile.objects.filter(user__username="newuser").exists())

    def test_existing_user_can_log_in(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "existing-user",
                "password": "StrongTestPassword123!",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_logged_in_user_can_log_out(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            dashboard_response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )


class MarketingPageTests(TestCase):
    def test_about_and_services_pages_render(self):
        about_response = self.client.get(reverse("about"))
        services_response = self.client.get(reverse("services"))

        self.assertEqual(about_response.status_code, 200)
        self.assertContains(about_response, "A greener choice for your plant community")
        self.assertContains(about_response, "Our mission")
        self.assertContains(about_response, "Our Team")
        self.assertContains(about_response, "Community statistics")
        self.assertContains(about_response, "Plants shared")
        self.assertContains(about_response, "Community impact")
        self.assertContains(about_response, "Why believe in Releaf?")
        self.assertEqual(services_response.status_code, 200)
        self.assertContains(services_response, "Natural Plants")
        self.assertContains(services_response, "Shop Gifts")
        self.assertContains(services_response, "Garden Care")
        self.assertContains(services_response, "Garden Accessories")

    def test_prototype_pages_use_bootstrap_layout_and_contact_map(self):
        home_response = self.client.get(reverse("home"))
        contact_response = self.client.get(reverse("contact"))

        self.assertContains(home_response, "bootstrap@5.3.9")
        self.assertContains(home_response, "Featured Plants")
        self.assertContains(home_response, "Why Releaf")
        self.assertContains(home_response, "Reviews")
        self.assertContains(home_response, "Made for people who love plants.")
        self.assertContains(contact_response, "Map of Chandigarh")
        self.assertContains(contact_response, "maps.google.com/maps")
        self.assertContains(contact_response, "Full name")

    def test_homepage_features_available_plants_and_recent_reviews(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(username="featured-owner")
        reviewer = user_model.objects.create_user(username="featured-reviewer")
        featured_plant = Plant.objects.create(
            name="Featured Fern",
            species="Boston fern",
            age=2,
            care_tips="Keep the soil moist.",
            care_level="easy",
            location="Chandigarh",
            image="plants/featured-fern.jpg",
            owner=owner,
        )
        reviewed_plant = Plant.objects.create(
            name="Reviewed Pothos",
            species="Epipremnum aureum",
            age=3,
            care_tips="Water weekly.",
            care_level="easy",
            status="ADOPTED",
            location="Chandigarh",
            image="plants/reviewed-pothos.jpg",
            owner=owner,
        )
        Review.objects.create(
            plant=reviewed_plant,
            user=reviewer,
            rating=5,
            comment="A lovely adoption experience.",
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(
            list(response.context["featured_plants"]),
            [featured_plant],
        )
        self.assertContains(response, "A lovely adoption experience.")

    def test_contact_form_saves_message_and_redirects(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "A plant lover",
                "email": "plantlover@example.com",
                "phone": "",
                "message": "I would like to know more about Releaf.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertContains(response, "Your message has been received")


class ProfileTests(TestCase):
    def test_user_can_edit_and_view_their_profile(self):
        user = get_user_model().objects.create_user(
            username="profile-owner",
            password="StrongTestPassword123!",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("edit_profile"),
            {
                "city": "Chandigarh",
                "bio": "I enjoy helping plants find new homes.",
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("profile_detail", kwargs={"user_id": user.pk}),
        )
        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.city, "Chandigarh")
        self.assertContains(response, "I enjoy helping plants find new homes.")

    def test_anonymous_users_cannot_edit_profiles(self):
        response = self.client.get(reverse("edit_profile"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('edit_profile')}",
        )

    def test_user_can_save_plant_matching_preferences(self):
        user = get_user_model().objects.create_user(
            username="preference-owner",
            password="StrongTestPassword123!",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("edit_profile"),
            {
                "city": "Chandigarh",
                "bio": "",
                "preferred_care_level": "easy",
                "preferred_size": "Medium",
                "preferred_environment": "indoor",
                "sunlight_preference": "Low sunlight",
            },
        )

        self.assertRedirects(
            response,
            reverse("profile_detail", kwargs={"user_id": user.pk}),
        )
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.city, "Chandigarh")
        self.assertEqual(profile.preferred_care_level, "easy")
        self.assertEqual(profile.preferred_size, "Medium")
        self.assertEqual(profile.preferred_environment, "indoor")
        self.assertEqual(profile.sunlight_preference, "Low sunlight")

    def test_profile_form_rejects_unsupported_image_extensions(self):
        user = get_user_model().objects.create_user(
            username="profile-image-user",
            password="StrongTestPassword123!",
        )
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="PNG")

        form = ProfileForm(
            data={"city": "", "bio": ""},
            files={
                "image": SimpleUploadedFile(
                    "profile.gif",
                    image_buffer.getvalue(),
                    content_type="image/gif",
                ),
            },
            instance=Profile(user=user),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)


class DashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="dashboard-member",
            password="StrongTestPassword123!",
        )
        self.adopter = user_model.objects.create_user(
            username="dashboard-adopter",
            password="StrongTestPassword123!",
        )
        self.other_owner = user_model.objects.create_user(
            username="dashboard-other-owner",
            password="StrongTestPassword123!",
        )
        self.owned_plant = Plant.objects.create(
            name="My Fern",
            species="Nephrolepis exaltata",
            age=2,
            care_tips="Keep the soil moist.",
            care_level="moderate",
            status="ADOPTED",
            adopted_by=self.adopter,
            location="Chandigarh",
            image="plants/my-fern.jpg",
            owner=self.user,
        )
        self.saved_plant = Plant.objects.create(
            name="Saved Pothos",
            species="Epipremnum aureum",
            age=1,
            care_tips="Water when the top soil feels dry.",
            care_level="easy",
            location="Mohali",
            image="plants/saved-pothos.jpg",
            owner=self.other_owner,
        )
        self.unrelated_plant = Plant.objects.create(
            name="Unrelated Lily",
            species="Spathiphyllum",
            age=1,
            care_tips="Keep the soil lightly moist.",
            care_level="moderate",
            location="Delhi",
            image="plants/unrelated-lily.jpg",
            owner=self.other_owner,
        )
        Favorite.objects.create(user=self.user, plant=self.saved_plant)
        Review.objects.create(
            plant=self.owned_plant,
            user=self.adopter,
            rating=5,
            comment="A wonderful adoption.",
        )

    def test_owner_dashboard_shows_plants_messages_and_received_reviews(self):
        participant_one, participant_two = sorted(
            (self.user, self.adopter),
            key=lambda participant: participant.pk,
        )
        conversation = Conversation.objects.create(
            participant_one=participant_one,
            participant_two=participant_two,
            plant=self.owned_plant,
        )
        Message.objects.create(
            conversation=conversation,
            sender=self.adopter,
            receiver=self.user,
            text="Is the plant settling in?",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Fern")
        self.assertContains(response, "Owner Dashboard")
        self.assertContains(response, "Is the plant settling in?")
        self.assertContains(response, "A wonderful adoption.")
        self.assertContains(response, "Messages")
        self.assertContains(response, "Profile")
        self.assertContains(response, "Adopter Dashboard")
        self.assertNotContains(response, "Saved Pothos")
        self.assertNotContains(response, "Unrelated Lily")
        self.assertEqual(len(response.context["my_plants"]), 1)
        self.assertEqual(len(response.context["reviews_received"]), 1)
        self.assertEqual(len(response.context["recent_messages"]), 1)

    def test_adopter_dashboard_shows_saved_plants_messages_and_authored_reviews(self):
        Favorite.objects.create(user=self.adopter, plant=self.saved_plant)
        participant_one, participant_two = sorted(
            (self.adopter, self.other_owner),
            key=lambda participant: participant.pk,
        )
        conversation = Conversation.objects.create(
            participant_one=participant_one,
            participant_two=participant_two,
            plant=self.saved_plant,
        )
        Message.objects.create(
            conversation=conversation,
            sender=self.other_owner,
            receiver=self.adopter,
            text="The pothos is ready for adoption.",
        )
        self.client.force_login(self.adopter)

        response = self.client.get(reverse("adopter_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adopter Dashboard")
        self.assertContains(response, "Saved Pothos")
        self.assertContains(response, "The pothos is ready for adoption.")
        self.assertContains(response, "A wonderful adoption.")
        self.assertContains(response, "My Reviews")
        self.assertContains(response, "Profile")
        self.assertNotContains(response, "Unrelated Lily")
        self.assertEqual(len(response.context["saved_plants"]), 1)
        self.assertEqual(len(response.context["recent_messages"]), 1)
        self.assertEqual(len(response.context["my_reviews"]), 1)

    def test_both_dashboards_require_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )
        adopter_response = self.client.get(reverse("adopter_dashboard"))
        self.assertRedirects(
            adopter_response,
            f"{reverse('login')}?next={reverse('adopter_dashboard')}",
        )


class CreatePlantTests(TestCase):
    def test_plant_form_rejects_unsupported_image_extensions(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="PNG")

        form = PlantForm(
            data={
                "name": "Pothos",
                "species": "Epipremnum aureum",
                "age": 1,
                "description": "A trailing plant for a bright room.",
                "care_tips": "Let the soil dry between watering.",
                "care_level": "easy",
                "size": "Medium",
                "sunlight_requirements": "Indirect sunlight",
                "watering_frequency": "Twice per week",
                "environment": "indoor",
                "location": "Kitchen",
            },
            files={
                "image": SimpleUploadedFile(
                    "pothos.gif",
                    image_buffer.getvalue(),
                    content_type="image/gif",
                ),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    def test_plant_form_rejects_invalid_image_content_even_with_allowed_extension(self):
        form = PlantForm(
            data={
                "name": "Pothos",
                "species": "Epipremnum aureum",
                "age": 1,
                "description": "A trailing plant for a bright room.",
                "care_tips": "Let the soil dry between watering.",
                "care_level": "easy",
                "size": "Medium",
                "sunlight_requirements": "Indirect sunlight",
                "watering_frequency": "Twice per week",
                "environment": "indoor",
                "location": "Kitchen",
            },
            files={
                "image": SimpleUploadedFile(
                    "not-an-image.jpg",
                    b"not an image",
                    content_type="image/jpeg",
                ),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    def test_anonymous_users_are_redirected_to_login(self):
        response = self.client.get(reverse("create_plant"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('create_plant')}",
        )

    def test_created_plant_is_assigned_to_logged_in_user(self):
        user = get_user_model().objects.create_user(
            username="planter",
            password="StrongTestPassword123!",
        )
        self.client.force_login(user)

        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="PNG")

        response = self.client.post(
            reverse("create_plant"),
            {
                "name": "Pothos",
                "species": "Epipremnum aureum",
                "age": 1,
                "description": "A trailing plant for a bright room.",
                "care_tips": "Let the soil dry between watering.",
                "care_level": "easy",
                "size": "Small",
                "sunlight_requirements": "Indirect sunlight",
                "watering_frequency": "Weekly",
                "environment": "indoor",
                "location": "Kitchen",
                "image": SimpleUploadedFile(
                    "pothos.png",
                    image_buffer.getvalue(),
                    content_type="image/png",
                ),
            },
        )

        self.assertRedirects(response, reverse("home"))
        plant = Plant.objects.get(name="Pothos")
        self.assertEqual(plant.owner, user)
        self.assertEqual(plant.status, "AVAILABLE")
        self.assertEqual(plant.size, "Small")


class EditPlantTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="listing-owner",
            password="StrongTestPassword123!",
        )
        self.adopter = user_model.objects.create_user(
            username="listing-adopter",
            password="StrongTestPassword123!",
        )
        self.other_user = user_model.objects.create_user(
            username="listing-outsider",
            password="StrongTestPassword123!",
        )
        self.plant = Plant.objects.create(
            name="Original Fern",
            species="Nephrolepis exaltata",
            age=2,
            description="A healthy fern.",
            care_tips="Keep the soil moist.",
            care_level="moderate",
            status="ADOPTED",
            adopted_by=self.adopter,
            size="Medium",
            sunlight_requirements="Indirect sunlight",
            watering_frequency="Twice per week",
            environment="indoor",
            location="Chandigarh",
            image="plants/original-fern.jpg",
            owner=self.owner,
        )

    def test_owner_can_edit_plant_details_without_changing_adoption_status(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("edit_plant", kwargs={"pk": self.plant.pk}),
            {
                "name": "Updated Fern",
                "species": "Nephrolepis exaltata",
                "age": 3,
                "description": "A thriving fern.",
                "care_tips": "Keep the soil evenly moist.",
                "care_level": "moderate",
                "size": "Large",
                "sunlight_requirements": "Bright indirect sunlight",
                "watering_frequency": "Twice per week",
                "environment": "indoor",
                "location": "Chandigarh",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, "Updated Fern")
        self.assertEqual(self.plant.owner, self.owner)
        self.assertEqual(self.plant.status, "ADOPTED")
        self.assertEqual(self.plant.adopted_by, self.adopter)

    def test_only_plant_owner_can_edit_listing(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse("edit_plant", kwargs={"pk": self.plant.pk})
        )

        self.assertEqual(response.status_code, 404)


class ReviewTests(TestCase):
    def test_review_belongs_to_a_plant_and_is_deleted_with_it(self):
        user = get_user_model().objects.create_user(
            username="reviewer",
            password="StrongTestPassword123!",
        )
        plant = Plant.objects.create(
            name="Fern",
            species="Nephrolepis exaltata",
            age=1,
            care_tips="Keep moist.",
            care_level="moderate",
            location="Bathroom",
            image="plants/fern.jpg",
            owner=user,
        )
        review = Review.objects.create(
            plant=plant,
            user=user,
            rating=5,
            comment="A lovely, healthy plant.",
        )

        self.assertEqual(plant.reviews.get(), review)

        plant.delete()
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())


class ReviewSubmissionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="reviewed-owner",
            password="StrongTestPassword123!",
        )
        self.adopter = user_model.objects.create_user(
            username="verified-adopter",
            password="StrongTestPassword123!",
        )
        self.other_user = user_model.objects.create_user(
            username="other-adopter",
            password="StrongTestPassword123!",
        )
        self.plant = Plant.objects.create(
            name="Adopted Fern",
            species="Nephrolepis exaltata",
            age=2,
            care_tips="Keep the soil moist.",
            care_level="moderate",
            status="ADOPTED",
            adopted_by=self.adopter,
            location="Chandigarh",
            image="plants/adopted-fern.jpg",
            owner=self.owner,
        )

    def test_recorded_adopter_can_review_and_rating_appears_on_owner_profile(self):
        self.client.force_login(self.adopter)
        review_url = reverse("leave_review", kwargs={"pk": self.plant.pk})

        response = self.client.post(
            review_url,
            {"rating": "5", "comment": "A lovely, healthy plant."},
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("plant_detail", kwargs={"pk": self.plant.pk}),
        )
        review = Review.objects.get()
        self.assertEqual(review.user, self.adopter)
        self.assertEqual(review.plant, self.plant)
        self.assertEqual(review.rating, 5)
        other_plant = Plant.objects.create(
            name="Adopted Pothos",
            species="Epipremnum aureum",
            age=1,
            care_tips="Water when the soil feels dry.",
            care_level="easy",
            status="ADOPTED",
            adopted_by=self.other_user,
            location="Chandigarh",
            image="plants/adopted-pothos.jpg",
            owner=self.owner,
        )
        Review.objects.create(
            plant=other_plant,
            user=self.other_user,
            rating=4,
            comment="Growing well in its new home.",
        )

        profile_response = self.client.get(
            reverse("profile_detail", kwargs={"user_id": self.owner.pk})
        )
        self.assertContains(profile_response, "4.5 / 5")
        self.assertContains(profile_response, "2 reviews")
        self.assertContains(profile_response, "A lovely, healthy plant.")
        self.assertContains(profile_response, "Growing well in its new home.")

    def test_review_is_available_only_to_recorded_adopter_and_only_once(self):
        review_url = reverse("leave_review", kwargs={"pk": self.plant.pk})
        self.client.force_login(self.other_user)

        blocked_response = self.client.post(
            review_url,
            {"rating": "4", "comment": "Not an adopter."},
            follow=True,
        )
        self.assertContains(blocked_response, "Only the recorded adopter")
        self.assertFalse(Review.objects.exists())

        self.client.force_login(self.adopter)
        for _ in range(2):
            self.client.post(
                review_url,
                {"rating": "4", "comment": "A thoughtful review."},
            )

        self.assertEqual(Review.objects.filter(plant=self.plant).count(), 1)

    def test_owner_and_adopter_before_completion_cannot_review(self):
        review_url = reverse("leave_review", kwargs={"pk": self.plant.pk})
        self.client.force_login(self.owner)
        owner_response = self.client.post(
            review_url,
            {"rating": "5", "comment": "Reviewing my own listing."},
            follow=True,
        )
        self.assertContains(owner_response, "Only the recorded adopter")
        self.assertFalse(Review.objects.exists())

        self.plant.status = "AVAILABLE"
        self.plant.save(update_fields=["status"])
        self.client.force_login(self.adopter)
        adopter_response = self.client.post(
            review_url,
            {"rating": "5", "comment": "The adoption is not complete."},
            follow=True,
        )
        self.assertContains(adopter_response, "Only the recorded adopter")
        self.assertFalse(Review.objects.exists())

    def test_review_form_rejects_ratings_outside_one_to_five(self):
        form = ReviewForm(data={"rating": "6", "comment": "Invalid rating."})

        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)


class PlantDetailTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="plant-owner",
            password="StrongTestPassword123!",
        )
        self.adopter = user_model.objects.create_user(
            username="plant-adopter",
            password="StrongTestPassword123!",
        )
        self.profile = Profile.objects.create(
            user=self.owner,
            city="Chandigarh",
            bio="I love helping plants find new homes.",
        )
        self.plant = Plant.objects.create(
            name="Pothos",
            species="Epipremnum aureum",
            age=1,
            description="A trailing plant with heart-shaped leaves.",
            care_tips="Water when the top soil feels dry.",
            care_level="easy",
            status="AVAILABLE",
            size="Medium",
            sunlight_requirements="Indirect sunlight",
            watering_frequency="Weekly",
            environment="indoor",
            location="Chandigarh",
            image="plants/pothos.png",
            owner=self.owner,
        )

    def test_public_page_shows_plant_details_and_owner_profile(self):
        response = self.client.get(
            reverse("plant_detail", kwargs={"pk": self.plant.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.plant.name)
        self.assertContains(response, "A trailing plant with heart-shaped leaves.")
        self.assertContains(response, "Water when the top soil feels dry.")
        self.assertContains(response, "Chandigarh")
        self.assertContains(response, reverse("profile_detail", kwargs={"user_id": self.owner.pk}))
        self.assertContains(response, reverse("contact_owner", kwargs={"pk": self.plant.pk}))

    def test_contact_button_sends_private_message_to_owner(self):
        self.client.force_login(self.adopter)

        response = self.client.post(
            reverse("contact_owner", kwargs={"pk": self.plant.pk}),
            {"text": "Is this plant still available?"},
        )

        self.assertRedirects(
            response,
            reverse("plant_detail", kwargs={"pk": self.plant.pk}),
        )
        message = Message.objects.get()
        self.assertEqual(message.sender, self.adopter)
        self.assertEqual(message.receiver, self.owner)
        self.assertEqual(message.text, "Is this plant still available?")
        self.assertEqual(message.conversation.plant, self.plant)

    def test_owner_cannot_send_a_message_to_themselves(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("contact_owner", kwargs={"pk": self.plant.pk}),
            {"text": "This should not be sent."},
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("plant_detail", kwargs={"pk": self.plant.pk}),
        )
        self.assertContains(response, "You cannot contact yourself")
        self.assertFalse(Message.objects.exists())

    def test_anonymous_contact_is_redirected_to_login(self):
        response = self.client.get(
            reverse("contact_owner", kwargs={"pk": self.plant.pk})
        )

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('contact_owner', kwargs={'pk': self.plant.pk})}",
        )


class AdoptionWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="adoption-owner",
            password="StrongTestPassword123!",
        )
        self.adopter = user_model.objects.create_user(
            username="adoption-adopter",
            password="StrongTestPassword123!",
        )
        self.other_adopter = user_model.objects.create_user(
            username="another-adopter",
            password="StrongTestPassword123!",
        )
        self.outsider = user_model.objects.create_user(
            username="adoption-outsider",
            password="StrongTestPassword123!",
        )
        self.plant = Plant.objects.create(
            name="Available Fern",
            species="Nephrolepis exaltata",
            age=2,
            care_tips="Keep the soil moist.",
            care_level="moderate",
            status="AVAILABLE",
            location="Chandigarh",
            image="plants/available-fern.jpg",
            owner=self.owner,
        )

    def test_adopter_can_request_available_plant_and_it_becomes_pending(self):
        plant_url = reverse("plant_detail", kwargs={"pk": self.plant.pk})
        request_url = reverse("request_adoption", kwargs={"pk": self.plant.pk})
        self.client.force_login(self.adopter)

        detail_response = self.client.get(plant_url)
        self.assertContains(detail_response, "Adopt Plant")

        response = self.client.post(request_url, follow=True)

        self.assertRedirects(response, plant_url)
        adoption_request = AdoptionRequest.objects.get()
        self.assertEqual(adoption_request.plant, self.plant)
        self.assertEqual(adoption_request.adopter, self.adopter)
        self.assertEqual(adoption_request.status, AdoptionRequest.STATUS_PENDING)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.status, "PENDING")
        self.assertContains(response, "Your adoption request is pending")
        self.assertNotContains(response, "Adopt Plant")

        repeated_response = self.client.post(request_url, follow=True)
        self.assertContains(repeated_response, "Your adoption request is already pending")
        self.assertEqual(AdoptionRequest.objects.count(), 1)

        self.client.force_login(self.other_adopter)
        blocked_response = self.client.post(request_url, follow=True)
        self.assertContains(blocked_response, "already being reviewed")
        self.assertEqual(AdoptionRequest.objects.count(), 1)

        self.client.force_login(self.owner)
        owner_detail = self.client.get(plant_url)
        self.assertNotContains(owner_detail, "Adopt Plant")

    def test_owner_acceptance_completes_adoption_and_records_adopter(self):
        self.client.force_login(self.adopter)
        self.client.post(reverse("request_adoption", kwargs={"pk": self.plant.pk}))
        adoption_request = AdoptionRequest.objects.get()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("accept_adoption", kwargs={"request_id": adoption_request.pk}),
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        adoption_request.refresh_from_db()
        self.plant.refresh_from_db()
        self.assertEqual(adoption_request.status, AdoptionRequest.STATUS_ACCEPTED)
        self.assertEqual(self.plant.status, "ADOPTED")
        self.assertEqual(self.plant.adopted_by, self.adopter)
        self.assertContains(response, "accepted the request")

        self.client.force_login(self.adopter)
        plant_detail = self.client.get(
            reverse("plant_detail", kwargs={"pk": self.plant.pk})
        )
        self.assertContains(plant_detail, "Leave review")

    def test_owner_rejection_reopens_plant_for_another_adopter(self):
        self.client.force_login(self.adopter)
        self.client.post(reverse("request_adoption", kwargs={"pk": self.plant.pk}))
        first_request = AdoptionRequest.objects.get()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("reject_adoption", kwargs={"request_id": first_request.pk}),
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        first_request.refresh_from_db()
        self.plant.refresh_from_db()
        self.assertEqual(first_request.status, AdoptionRequest.STATUS_REJECTED)
        self.assertEqual(self.plant.status, "AVAILABLE")
        self.assertIsNone(self.plant.adopted_by)

        self.client.force_login(self.other_adopter)
        self.client.post(reverse("request_adoption", kwargs={"pk": self.plant.pk}))
        self.assertEqual(AdoptionRequest.objects.count(), 2)
        self.assertTrue(
            AdoptionRequest.objects.filter(
                plant=self.plant,
                adopter=self.other_adopter,
                status=AdoptionRequest.STATUS_PENDING,
            ).exists()
        )

    def test_only_plant_owner_can_decide_requests_and_dashboards_show_status(self):
        self.client.force_login(self.adopter)
        self.client.post(reverse("request_adoption", kwargs={"pk": self.plant.pk}))
        adoption_request = AdoptionRequest.objects.get()

        self.client.force_login(self.outsider)
        accept_response = self.client.post(
            reverse("accept_adoption", kwargs={"request_id": adoption_request.pk})
        )
        reject_response = self.client.post(
            reverse("reject_adoption", kwargs={"request_id": adoption_request.pk})
        )
        self.assertEqual(accept_response.status_code, 404)
        self.assertEqual(reject_response.status_code, 404)

        self.client.force_login(self.owner)
        owner_dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(owner_dashboard, "Adoption Requests")
        self.assertContains(owner_dashboard, "Accept")
        self.assertEqual(len(owner_dashboard.context["adoption_requests"]), 1)

        self.client.force_login(self.adopter)
        adopter_dashboard = self.client.get(reverse("adopter_dashboard"))
        self.assertContains(adopter_dashboard, "My Adoption Requests")
        self.assertContains(adopter_dashboard, "Pending")
        self.assertEqual(len(adopter_dashboard.context["my_adoption_requests"]), 1)

    def test_anonymous_user_must_log_in_to_request_adoption(self):
        response = self.client.post(
            reverse("request_adoption", kwargs={"pk": self.plant.pk})
        )

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('request_adoption', kwargs={'pk': self.plant.pk})}",
        )
        self.assertFalse(AdoptionRequest.objects.exists())


class FavoriteTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="favorite-owner",
            password="StrongTestPassword123!",
        )
        self.adopter = user_model.objects.create_user(
            username="favorite-adopter",
            password="StrongTestPassword123!",
        )
        self.plant = Plant.objects.create(
            name="Peace Lily",
            species="Spathiphyllum",
            age=2,
            care_tips="Keep the soil lightly moist.",
            care_level="moderate",
            size="Medium",
            environment="indoor",
            location="Chandigarh",
            image="plants/peace-lily.jpg",
            owner=self.owner,
        )

    def test_adopter_can_save_and_remove_a_plant(self):
        self.client.force_login(self.adopter)
        toggle_url = reverse("toggle_favorite", kwargs={"pk": self.plant.pk})

        response = self.client.post(
            toggle_url,
            {"next": reverse("home")},
            follow=True,
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(
            Favorite.objects.filter(user=self.adopter, plant=self.plant).exists()
        )

        response = self.client.post(
            toggle_url,
            {"next": reverse("home")},
            follow=True,
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(
            Favorite.objects.filter(user=self.adopter, plant=self.plant).exists()
        )

    def test_favorites_page_shows_only_current_users_saved_plants(self):
        other_user = get_user_model().objects.create_user(
            username="another-adopter",
            password="StrongTestPassword123!",
        )
        Favorite.objects.create(user=self.adopter, plant=self.plant)
        Favorite.objects.create(user=other_user, plant=self.plant)
        self.client.force_login(self.adopter)

        response = self.client.get(reverse("favorites"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Peace Lily")
        self.assertEqual(len(response.context["saved_plants"]), 1)

    def test_user_cannot_save_their_own_plant(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("toggle_favorite", kwargs={"pk": self.plant.pk}),
            follow=True,
        )

        self.assertContains(response, "You cannot save your own plant listing")
        self.assertFalse(Favorite.objects.exists())

    def test_anonymous_user_is_redirected_to_login_to_save(self):
        response = self.client.post(
            reverse("toggle_favorite", kwargs={"pk": self.plant.pk})
        )

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('toggle_favorite', kwargs={'pk': self.plant.pk})}",
        )


class MessageTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.sender = user_model.objects.create_user(
            username="sender",
            password="StrongTestPassword123!",
        )
        self.receiver = user_model.objects.create_user(
            username="receiver",
            password="StrongTestPassword123!",
        )
        self.conversation = Conversation.objects.create(
            participant_one=self.sender,
            participant_two=self.receiver,
        )

    def test_message_links_sender_and_receiver(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.sender,
            receiver=self.receiver,
            text="Hello from Releaf.",
        )

        self.assertEqual(self.conversation.messages.get(), message)
        self.assertEqual(self.sender.sender.get(), message)
        self.assertEqual(self.receiver.receiver.get(), message)
        self.assertIsNotNone(message.created_at)
        self.assertFalse(message.is_read)

    def test_deleting_either_user_deletes_their_messages(self):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.sender,
            receiver=self.receiver,
            text="Hello.",
        )

        self.sender.delete()

        self.assertEqual(Message.objects.count(), 0)


class MessageInboxTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="message-owner",
            password="StrongTestPassword123!",
        )
        self.adopter = user_model.objects.create_user(
            username="message-adopter",
            password="StrongTestPassword123!",
        )
        self.other_user = user_model.objects.create_user(
            username="message-outsider",
            password="StrongTestPassword123!",
        )
        participant_one, participant_two = sorted(
            (self.owner, self.adopter),
            key=lambda participant: participant.pk,
        )
        self.conversation = Conversation.objects.create(
            participant_one=participant_one,
            participant_two=participant_two,
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.adopter,
            receiver=self.owner,
            text="Is this plant still available?",
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.owner,
            receiver=self.adopter,
            text="Yes, it is available.",
        )

    def test_inbox_and_sent_items_show_relevant_conversations(self):
        self.client.force_login(self.adopter)

        inbox_response = self.client.get(reverse("message_inbox"))
        sent_response = self.client.get(
            reverse("message_inbox"),
            {"folder": "sent"},
        )

        self.assertContains(inbox_response, "message-owner")
        self.assertContains(inbox_response, "Yes, it is available.")
        self.assertContains(inbox_response, "1 unread")
        self.assertContains(inbox_response, 'aria-label="1 unread messages"')
        self.assertEqual(inbox_response.context["unread_message_count"], 1)
        self.assertContains(sent_response, "message-owner")
        self.assertContains(sent_response, "Is this plant still available?")

    def test_opening_conversation_marks_only_received_messages_as_read(self):
        self.client.force_login(self.adopter)

        self.client.get(
            reverse(
                "conversation_detail",
                kwargs={"conversation_id": self.conversation.pk},
            )
        )

        received_message = Message.objects.get(sender=self.owner)
        sent_message = Message.objects.get(sender=self.adopter)
        self.assertTrue(received_message.is_read)
        self.assertFalse(sent_message.is_read)

    def test_conversation_participant_can_reply(self):
        self.client.force_login(self.adopter)

        response = self.client.post(
            reverse(
                "conversation_detail",
                kwargs={"conversation_id": self.conversation.pk},
            ),
            {"text": "Great, thank you."},
        )

        self.assertRedirects(
            response,
            reverse(
                "conversation_detail",
                kwargs={"conversation_id": self.conversation.pk},
            ),
        )
        reply = Message.objects.latest("created_at")
        self.assertEqual(reply.sender, self.adopter)
        self.assertEqual(reply.receiver, self.owner)
        self.assertEqual(reply.conversation, self.conversation)

    def test_non_participant_cannot_read_conversation(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse(
                "conversation_detail",
                kwargs={"conversation_id": self.conversation.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
