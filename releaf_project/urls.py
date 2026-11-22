"""
URL configuration for releaf_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from plants import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('who-we-are/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('profiles/<int:user_id>/', views.profile_detail, name='profile_detail'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/adopter/', views.adopter_dashboard, name='adopter_dashboard'),
    path('plants/<int:pk>/', views.plant_detail, name='plant_detail'),
    path('plants/<int:pk>/adopt/', views.request_adoption, name='request_adoption'),
    path(
        'adoption-requests/<int:request_id>/accept/',
        views.accept_adoption,
        name='accept_adoption',
    ),
    path(
        'adoption-requests/<int:request_id>/reject/',
        views.reject_adoption,
        name='reject_adoption',
    ),
    path('plants/<int:pk>/edit/', views.edit_plant, name='edit_plant'),
    path('plants/<int:pk>/contact/', views.contact_owner, name='contact_owner'),
    path('plants/<int:pk>/review/', views.leave_review, name='leave_review'),
    path('favorites/', views.favorites, name='favorites'),
    path('plants/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('messages/', views.message_inbox, name='message_inbox'),
    path(
        'messages/<int:conversation_id>/',
        views.conversation_detail,
        name='conversation_detail',
    ),
    path('create-plant/', views.create_plant, name='create_plant'),
    path('register/', views.register, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='plants/login.html'),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
