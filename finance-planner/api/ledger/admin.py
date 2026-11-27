from django.contrib import admin
from django.db.models import Model
from django.http import HttpRequest

from ledger.models import Account, Category, Operation, Transfer


class ReadOnlyAdmin(admin.ModelAdmin):
    # Данные учёта меняются только через API: правила сервисов админка обходила бы.
    # Признак читает админка пользователей: эти строки уходят каскадом вместе с владельцем
    is_deleted_with_owner = True

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False


@admin.register(Account)
class AccountAdmin(ReadOnlyAdmin):
    list_display = ("name", "user", "kind", "currency", "initial_balance", "is_archived", "created_at")
    list_filter = ("kind", "is_archived")
    list_select_related = ("user",)
    search_fields = ("name", "user__username")


@admin.register(Category)
class CategoryAdmin(ReadOnlyAdmin):
    list_display = ("name", "kind", "user")
    list_filter = ("kind",)
    list_select_related = ("user",)
    search_fields = ("name", "user__username")


@admin.register(Operation)
class OperationAdmin(ReadOnlyAdmin):
    list_display = ("date", "user", "account", "kind", "amount", "category", "note")
    list_filter = ("kind",)
    list_select_related = ("user", "account", "category")
    search_fields = ("note", "user__username")


@admin.register(Transfer)
class TransferAdmin(ReadOnlyAdmin):
    list_display = ("date", "user", "from_account", "to_account", "amount_out", "amount_in")
    list_select_related = ("user", "from_account", "to_account")
    search_fields = ("note", "user__username")
