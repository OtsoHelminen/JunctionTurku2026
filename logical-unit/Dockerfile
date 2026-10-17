FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/alerts.db \
    RULES_PATH=/srv/config/rules.yaml \
    SEED_PATH=/srv/config/resolvers.yaml

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config

# Ei ajeta roottina. /data on volyymi, jossa SQLite-tiedosto säilyy kontin uudelleenluonnissa.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data && chown appuser /data
USER appuser
VOLUME ["/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"

# Yksi prosessi: ajastin ja SQLite-kirjoittaja pysyvät yksinä.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
