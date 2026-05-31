from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render

from ai_assistant.location_utils import verify_german_location_with_google

from .forms import UserProfileForm
from .models import UserProfile


@login_required
def profile_detail(request):
    profile, _created = UserProfile.objects.get_or_create(
        user=request.user,
    )

    if request.method == "POST":
        form = UserProfileForm(
            request.POST,
            instance=profile,
        )

        if form.is_valid():
            profile = form.save(commit=False)

        profile.home_location = profile.formatted_address

        if profile.home_location:
            normalized = verify_german_location_with_google(
                profile.home_location,
            )
            profile.normalized_home_location = normalized

            profile.save()

            messages.success(
                request,
                "Profile updated successfully.",
            )

            return redirect("accounts:profile_detail")
    else:
        form = UserProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile_detail.html",
        {
            "form": form,
            "profile": profile,
        },
    )
