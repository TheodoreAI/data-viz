# ---- frontend build stage ----
FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY vite.config.js ./
COPY src ./src
RUN yarn build

# ---- python runtime stage ----
FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY migrations ./migrations
COPY templates ./templates
COPY static ./static
COPY --from=frontend /app/static/dist ./static/dist

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
EXPOSE 8081

CMD ["sh", "-c", "flask db upgrade && flask warm-cache && gunicorn --bind 0.0.0.0:${PORT:-8081} --timeout 90 app:app"]