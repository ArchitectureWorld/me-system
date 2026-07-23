FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
COPY examples ./examples

RUN pip install --no-cache-dir .

EXPOSE 8765

CMD ["python", "-m", "me_system.experience", "--host", "0.0.0.0", "--port", "8765"]
