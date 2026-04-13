FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8003

# Uvicorn acts to keep the process alive and running the Redis listener in the background via lifespan events
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
