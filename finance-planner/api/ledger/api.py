from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Status
from ninja.pagination import PageNumberPagination, paginate

from ledger import services
from ledger.models import Account, Category, Operation
from ledger.schemas import (
    AccountCreateInput,
    AccountListOut,
    AccountOut,
    AccountUpdateInput,
    CategoryCreateInput,
    CategoryKindValue,
    CategoryListOut,
    CategoryOut,
    CategoryUpdateInput,
    OperationCreateInput,
    OperationFilter,
    OperationOut,
    OperationSort,
    OperationUpdateInput,
)

OPERATIONS_PAGE_SIZE = 50
OPERATIONS_MAX_PAGE_SIZE = 100

# При равной дате порядок задаёт id в том же направлении, иначе строки одного дня менялись бы местами между страницами
OPERATION_ORDERINGS = {"-date": ("-date", "-id"), "date": ("date", "id")}


class OperationPagination(PageNumberPagination):
    # Страница за концом списка отдаёт пустой список без запроса строк: огромный номер страницы
    # иначе превратился бы в OFFSET больше bigint, и PostgreSQL ответил бы ошибкой
    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: PageNumberPagination.Input,
        request: HttpRequest,
        **params: object,
    ) -> dict[str, object]:
        page_size = self._get_page_size(pagination.page_size)
        page_start = (pagination.page - 1) * page_size
        page_end = page_start + page_size
        total_count = queryset.count()

        if page_start >= total_count:
            return {self.items_attribute: [], "count": total_count}

        return {self.items_attribute: queryset[page_start:page_end], "count": total_count}


accounts_router = Router(tags=["Счета"])
categories_router = Router(tags=["Категории"])
operations_router = Router(tags=["Операции"])


@accounts_router.get("", response={200: AccountListOut}, summary="Счета с балансами и общий баланс")
def list_accounts(request: HttpRequest) -> dict[str, object]:
    accounts = list(Account.objects.for_user(request.user).with_balance().order_by("id"))
    total_balance = services.sum_balances(accounts)

    return {"items": accounts, "total_balance": total_balance}


@accounts_router.post("", response={201: AccountOut}, summary="Создать счёт")
def create_account(request: HttpRequest, payload: AccountCreateInput) -> Status[Account]:
    account = services.create_account(
        request.user,
        name=payload.name,
        kind=payload.kind,
        currency=payload.currency,
        initial_balance=payload.initial_balance,
    )

    return Status(201, account)


@accounts_router.get("/{account_id}", response={200: AccountOut}, summary="Один счёт")
def read_account(request: HttpRequest, account_id: int) -> Account:
    accounts = Account.objects.for_user(request.user).with_balance()

    return get_object_or_404(accounts, id=account_id)


@accounts_router.patch("/{account_id}", response={200: AccountOut}, summary="Изменить счёт или перенести в архив")
def update_account(request: HttpRequest, account_id: int, payload: AccountUpdateInput) -> Account:
    account = get_object_or_404(Account.objects.for_user(request.user), id=account_id)
    changes = payload.model_dump(exclude_unset=True)

    return services.update_account(account, changes)


@accounts_router.delete("/{account_id}", response={204: None}, summary="Удалить счёт без ссылок")
def delete_account(request: HttpRequest, account_id: int) -> Status[None]:
    account = get_object_or_404(Account.objects.for_user(request.user), id=account_id)
    services.delete_account(account)

    return Status(204, None)


@categories_router.get("", response={200: CategoryListOut}, summary="Общие и свои категории")
def list_categories(request: HttpRequest, kind: CategoryKindValue | None = None) -> dict[str, object]:
    categories = Category.objects.visible_to(request.user)

    if kind is not None:
        categories = categories.filter(kind=kind)

    return {"items": categories.order_by("kind", "name", "id")}


@categories_router.post("", response={201: CategoryOut}, summary="Создать свою категорию")
def create_category(request: HttpRequest, payload: CategoryCreateInput) -> Status[Category]:
    category = services.create_category(request.user, payload.name, payload.kind)

    return Status(201, category)


@categories_router.patch("/{category_id}", response={200: CategoryOut}, summary="Переименовать свою категорию")
def rename_category(request: HttpRequest, category_id: int, payload: CategoryUpdateInput) -> Category:
    category = get_object_or_404(Category.objects.visible_to(request.user), id=category_id)

    return services.rename_category(request.user, category, payload.name)


@categories_router.delete("/{category_id}", response={204: None}, summary="Удалить свою категорию без ссылок")
def delete_category(request: HttpRequest, category_id: int) -> Status[None]:
    category = get_object_or_404(Category.objects.visible_to(request.user), id=category_id)
    services.delete_category(category)

    return Status(204, None)


@operations_router.get("", response=list[OperationOut], summary="История операций с фильтрами")
@paginate(OperationPagination, page_size=OPERATIONS_PAGE_SIZE, max_page_size=OPERATIONS_MAX_PAGE_SIZE)
def list_operations(request: HttpRequest, filters: Query[OperationFilter], sort: OperationSort = "-date") -> QuerySet[Operation]:
    operations = filters.filter(Operation.objects.for_user(request.user))
    ordering = OPERATION_ORDERINGS[sort]

    return operations.order_by(*ordering)


@operations_router.post("", response={201: OperationOut}, summary="Создать доход или расход")
def create_operation(request: HttpRequest, payload: OperationCreateInput) -> Status[Operation]:
    operation = services.create_operation(
        request.user,
        kind=payload.kind,
        account_id=payload.account_id,
        category_id=payload.category_id,
        amount=payload.amount,
        operation_date=payload.date,
        note=payload.note,
    )

    return Status(201, operation)


@operations_router.get("/{operation_id}", response={200: OperationOut}, summary="Одна операция")
def read_operation(request: HttpRequest, operation_id: int) -> Operation:
    return get_object_or_404(Operation.objects.for_user(request.user), id=operation_id)


@operations_router.patch("/{operation_id}", response={200: OperationOut}, summary="Изменить доход или расход")
def update_operation(request: HttpRequest, operation_id: int, payload: OperationUpdateInput) -> Operation:
    operations = Operation.objects.for_user(request.user).select_related("account")
    operation = get_object_or_404(operations, id=operation_id)
    changes = payload.model_dump(exclude_unset=True)

    return services.update_operation(request.user, operation, changes)


@operations_router.delete("/{operation_id}", response={204: None}, summary="Удалить доход или расход")
def delete_operation(request: HttpRequest, operation_id: int) -> Status[None]:
    operation = get_object_or_404(Operation.objects.for_user(request.user), id=operation_id)
    services.delete_operation(operation)

    return Status(204, None)
