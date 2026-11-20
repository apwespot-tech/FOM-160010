from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class PlannerUserAdmin(UserAdmin):
    # Почта и имя у пользователя планера не используются, поэтому в карточке их нет
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Часовой пояс", {"fields": ("time_zone",)}),
        ("Права доступа", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )

    list_display = ("username", "time_zone", "is_staff", "date_joined")
    search_fields = ("username",)
