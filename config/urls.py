from django.http import JsonResponse
from django.urls import path

from companies.views import peer_group


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health, name="health"),
    path("companies/<int:company_id>/peers", peer_group, name="peer-group"),
]
