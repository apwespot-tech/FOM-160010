from django.contrib import admin
from django.urls import path

from finance_planner.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
