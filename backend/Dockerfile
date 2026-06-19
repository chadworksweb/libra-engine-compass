# Libra Engine Compass -- the scoring service. Deliberately lean: no Playwright,
# no pg_dump, no git/ots (those are RC application concerns). psycopg ships a
# binary wheel, so no system Postgres client is needed.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Writable data dir (sqlite fallback only; prod uses the Postgres DSN) + a
# non-root runtime user.
RUN mkdir -p data \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8012

CMD ["uvicorn", "app.lec_main:app", "--host", "0.0.0.0", "--port", "8012"]
