FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DRY_RUN=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY shorts_pipeline ./shorts_pipeline
COPY .env.example ./

RUN mkdir -p /app/output /app/data
VOLUME ["/app/output", "/app/data"]
CMD ["python", "-m", "shorts_pipeline", "run", "--daemon", "--interval-hours", "24"]
