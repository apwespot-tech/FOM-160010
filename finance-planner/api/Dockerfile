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

ARG INSTALL_DEV=true
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv <<EOF
case "$INSTALL_DEV" in
    true) uv sync --locked ;;
    false) uv sync --locked --no-dev ;;
    *) echo "Аргумент INSTALL_DEV принимает значения true или false, а получено: $INSTALL_DEV" >&2; exit 1 ;;
esac
EOF

COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
