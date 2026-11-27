from collections.abc import Callable

from django.http import HttpResponse

# Тип фикстуры send_json из conftest.py: тесты всех приложений объявляют её одинаково
JsonSender = Callable[..., HttpResponse]
