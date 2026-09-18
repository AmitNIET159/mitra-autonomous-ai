FROM python:3.11-slim

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Configuration for Cloud / Hugging Face Spaces / Render
ENV PORT=7860
ENV SIMULATION_MODE=true
ENV CORS_ORIGINS=*
ENV APP_ENV=production
ENV AI_PROVIDER_PREFERENCE=auto

EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
