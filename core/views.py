from django.shortcuts import render


def home(request):
    return render(request, "core/home.html")


def dashboard(request):
    return render(request, "core/dashboard.html")


def about(request):
    return render(request, "core/about.html")


def pricing(request):
    return render(request, "core/pricing.html")
