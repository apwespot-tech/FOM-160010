from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# Список записан в самой миграции, а не взят из кода приложения: миграция должна давать тот же результат и после его правок
COMMON_CATEGORIES = [
    ("income", "Зарплата"),
    ("income", "Подарки"),
    ("income", "Прочие доходы"),
    ("expense", "Продукты"),
    ("expense", "Транспорт"),
    ("expense", "Жильё"),
    ("expense", "Связь"),
    ("expense", "Здоровье"),
    ("expense", "Одежда"),
    ("expense", "Развлечения"),
    ("expense", "Образование"),
    ("expense", "Кафе"),
    ("expense", "Подписки"),
    ("expense", "Прочие расходы"),
]


def create_common_categories(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Category = apps.get_model("ledger", "Category")
    categories = [Category(user=None, kind=kind, name=name) for kind, name in COMMON_CATEGORIES]

    # После отката к 0001 категории остаются в базе, поэтому при повторном применении уже существующие пропускаются
    Category.objects.bulk_create(categories, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("ledger", "0001_initial"),
    ]

    operations = [
        # Обратный шаг ничего не удаляет: на общие категории могут ссылаться операции пользователей
        migrations.RunPython(create_common_categories, migrations.RunPython.noop),
    ]
