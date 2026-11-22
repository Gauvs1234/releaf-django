from io import BytesIO

from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import ContactMessage, Message, Plant, Review
from .forms import PlantForm


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
            location="Living room",
            image="plants/snake-plant.jpg",
            owner=self.user,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Snake Plant")
        self.assertContains(response, "Dracaena trifasciata")
        self.assertContains(response, "Living room")
        self.assertQuerySetEqual(
            response.context["plants"],
            [Plant.objects.get(name="Snake Plant")],
        )

    def test_home_filters_plants_by_species_location_and_care_level(self):
        Plant.objects.create(
            name="Snake Plant",
            species="Dracaena trifasciata",
            age=2,
            care_tips="Water sparingly.",
            care_level="easy",
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
            location="Bathroom",
            image="plants/fern.jpg",
            owner=self.user,
        )

        response = self.client.get(
            reverse("home"),
            {
                "species": "Dracaena trifasciata",
                "location": "Living room",
                "care_level": "easy",
            },
        )

        self.assertContains(response, "Snake Plant")
        self.assertNotContains(response, "Fern")


class RegistrationTests(TestCase):
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


class MarketingPageTests(TestCase):
    def test_about_and_services_pages_render(self):
        about_response = self.client.get(reverse("about"))
        services_response = self.client.get(reverse("services"))

        self.assertEqual(about_response.status_code, 200)
        self.assertContains(about_response, "A greener world starts")
        self.assertEqual(services_response.status_code, 200)
        self.assertContains(services_response, "Plant adoption")

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


class CreatePlantTests(TestCase):
    def test_plant_form_rejects_unsupported_image_extensions(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="PNG")

        form = PlantForm(
            data={
                "name": "Pothos",
                "species": "Epipremnum aureum",
                "age": 1,
                "care_tips": "Let the soil dry between watering.",
                "care_level": "easy",
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
                "care_tips": "Let the soil dry between watering.",
                "care_level": "easy",
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

    def test_message_links_sender_and_receiver(self):
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            text="Hello from Releaf.",
        )

        self.assertEqual(self.sender.sender.get(), message)
        self.assertEqual(self.receiver.receiver.get(), message)
        self.assertIsNotNone(message.created_at)

    def test_deleting_either_user_deletes_their_messages(self):
        Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            text="Hello.",
        )

        self.sender.delete()

        self.assertEqual(Message.objects.count(), 0)
