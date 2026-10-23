# api/Dockerfile — образ бэкенда (слайд 16)
FROM php:8.3-cli

RUN apt-get update && apt-get install -y libpq-dev libonig-dev libzip-dev unzip git \
    && docker-php-ext-install pdo_pgsql mbstring zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
COPY . .
RUN composer install --no-interaction --prefer-dist

# При старте: .env из образца, ключ, пароль БД, миграции, запуск сервера.
# Пароль пишем в .env: `artisan serve` не передаёт серверу переменные окружения контейнера.
CMD ["sh", "-c", "[ -f .env ] || cp .env.example .env; grep -q '^APP_KEY=base64' .env || php artisan key:generate --force; sed -i '/^DB_PASSWORD=/d' .env; echo \"DB_PASSWORD=$DB_PASSWORD\" >> .env; php artisan migrate --force; php artisan serve --host=0.0.0.0 --port=8000"]
