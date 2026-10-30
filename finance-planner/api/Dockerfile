FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN useradd --create-home --uid 1000 app

WORKDIR /app

RUN chown app:app /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
