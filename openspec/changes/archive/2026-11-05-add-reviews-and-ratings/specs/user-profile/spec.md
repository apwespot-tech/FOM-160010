# Spec Delta

## MODIFIED Requirements

### Requirement: Представление профиля
Профиль SHALL содержать: `id` (UUID), `phone` (E.164), `name`, `birth_date`, вычисляемый `age` (полных лет на текущую дату), `email`, `telegram`, `about`, `city` (`id`, `name`), `interests` (список категорий `id`, `name`, `icon` по `id`), `avatar_id`, `cover_id`, `created_at`, `stats` (`organized_count`, `attended_count`), `ratings` (`as_organizer`, `as_participant`), `roles` и `profile_completed`. Отсутствующие необязательные значения передаются как `null`, отсутствие интересов — пустым списком.

#### Scenario: Возраст вычисляется по дате рождения
- **WHEN** у пользователя `birth_date` равна `2000-11-01`, а текущая дата `2026-10-31`
- **THEN** в профиле `age` равен 25

#### Scenario: День рождения сегодня
- **WHEN** у пользователя `birth_date` равна `2000-10-31`, а текущая дата `2026-10-31`
- **THEN** в профиле `age` равен 26

#### Scenario: Новый профиль
- **WHEN** пользователь только что заполнил имя и дату рождения
- **THEN** `about`, `city`, `avatar_id`, `cover_id` равны `null`, `interests` — пустой список, `stats` = `{organized_count: 0, attended_count: 0}`, `ratings` = `{as_organizer: {average: null, count: 0}, as_participant: {average: null, count: 0}}`, `created_at` — момент первого входа, поля `photo_url` в ответе нет

## ADDED Requirements

### Requirement: Рейтинги в профиле
Профиль SHALL содержать `ratings.as_organizer` и `ratings.as_participant` — каждый в виде `average` (рейтинг по отзывам вида `organizer` или `participant` соответственно, `null` при числе отзывов меньше 3) и `count` (число отзывов этого вида). Рейтинги MUST возвращаться в `GET /profile`, `GET /profile/{id}` и ответах изменения профиля.

#### Scenario: Оба рейтинга
- **WHEN** у пользователя 12 отзывов как об организаторе со средним 4.8 и 7 отзывов как об участнике со средним 4.6
- **THEN** `ratings` = `{as_organizer: {average: 4.8, count: 12}, as_participant: {average: 4.6, count: 7}}`

#### Scenario: Мало отзывов
- **WHEN** у пользователя два отзыва как об участнике
- **THEN** `ratings.as_participant` = `{average: null, count: 2}`

#### Scenario: Ровно три отзыва
- **WHEN** у пользователя три отзыва как об организаторе с оценками 4, 4 и 5
- **THEN** `ratings.as_organizer` = `{average: 4.3, count: 3}`

#### Scenario: Чужой профиль
- **WHEN** участник общего мероприятия открывает профиль организатора
- **THEN** ответ содержит рейтинги организатора так же, как их видит владелец
