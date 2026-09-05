FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY templates ./templates
COPY static ./static

ENV STUDIO_HOST=0.0.0.0
ENV STUDIO_PORT=8091
ENV STUDIO_DATA_DIR=/data
EXPOSE 8091

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091", "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]
