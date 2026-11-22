from .models import Plant, Profile


def _text_matches(value, preference):
    value = " ".join(value.casefold().split())
    preference = " ".join(preference.casefold().split())
    return bool(value and preference) and (
        preference in value or value in preference
    )


def calculate_match(plant, user_preferences):
    score = 0
    if (
        user_preferences.preferred_care_level
        and plant.care_level == user_preferences.preferred_care_level
    ):
        score += 40
    if user_preferences.city and _text_matches(
        plant.location,
        user_preferences.city,
    ):
        score += 30
    if (
        user_preferences.preferred_size
        and plant.size.strip().casefold()
        == user_preferences.preferred_size.strip().casefold()
    ):
        score += 20
    if (
        user_preferences.preferred_environment
        and plant.environment
        in {user_preferences.preferred_environment, "both"}
    ):
        score += 25
    if user_preferences.sunlight_preference and _text_matches(
        plant.sunlight_requirements,
        user_preferences.sunlight_preference,
    ):
        score += 25
    return score


def score_plant_match(plant, profile):
    return calculate_match(plant, profile)


def get_recommended_plants(user):
    profile = Profile.objects.filter(user=user).first()
    if profile is None:
        return []

    plants = (
        Plant.objects.filter(status="AVAILABLE")
        .exclude(owner=user)
        .select_related("owner")
    )
    scored_plants = []
    for plant in plants:
        score = calculate_match(plant, profile)
        if score:
            scored_plants.append({"plant": plant, "score": score})

    return sorted(
        scored_plants,
        key=lambda recommendation: (
            -recommendation["score"],
            recommendation["plant"].pk,
        ),
    )[:6]


def has_recommendation_preferences(profile):
    return bool(
        profile
        and (
            profile.city
            or profile.preferred_care_level
            or profile.preferred_size
            or profile.preferred_environment
            or profile.sunlight_preference
        )
    )
