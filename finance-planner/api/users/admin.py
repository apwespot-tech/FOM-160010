from django.apps import apps
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from users.models import User

DeletionSummary = tuple[list[object], dict[str, int], set[str], list[object]]


def collect_owner_cascade_names(admin_site: AdminSite) -> set[str]:
    # Строки приложений, чья админка только для чтения, удаляются каскадом вместе с пользователем.
    # Права удалять их напрямую для этого не нужно, иначе админка отказала бы в удалении любого пользователя с данными
    cascade_names = set()

    for model in apps.get_models():
        is_owner_cascade = admin_site.is_registered(model) and getattr(admin_site.get_model_admin(model), "is_deleted_with_owner", False)

        if is_owner_cascade:
            cascade_names.add(model._meta.verbose_name)

    return cascade_names


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

    def get_deleted_objects(self, objs: QuerySet[User] | list[User], request: HttpRequest) -> DeletionSummary:
        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        cascade_names = collect_owner_cascade_names(self.admin_site)

        return deleted_objects, model_count, perms_needed - cascade_names, protected
