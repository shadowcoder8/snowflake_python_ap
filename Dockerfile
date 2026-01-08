
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final
FROM python:3.12-slim

WORKDIR /app

# Create a non-root user
RUN groupadd -r appuser && useradd -r -m -s /bin/bash -g appuser appuser

# Install runtime utilities (ps, curl) for debugging
RUN apt-get update && \
    apt-get install -y --no-install-recommends procps curl && \
    rm -rf /var/lib/apt/lists/*


COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

COPY . .

# Change ownership
# RUN chown -R appuser:appuser /app

# USER appuser

EXPOSE 8000

CMD ["gunicorn", "-c", "deployment/gunicorn.conf.py", "app.main:app"]
