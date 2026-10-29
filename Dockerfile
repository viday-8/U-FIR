# Untested in the build environment (no Docker available there). Intended for the pilot deployment path.
FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=ui /ui/dist frontend/dist
WORKDIR /srv/backend
ENV ENV=production STORAGE_DIR=/data/storage DATABASE_URL=sqlite:////data/ufir.db
VOLUME /data
EXPOSE 8000
# Seed demo data only on first start; set JWT_SECRET at run time (the app refuses the default when ENV=production).
CMD ["sh", "-c", "[ -f /data/ufir.db ] || (python -m app.seed && python -m app.process); uvicorn app.main:app --host 0.0.0.0 --port 8000"]
