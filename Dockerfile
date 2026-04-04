FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NETWORK=ethereum-sepolia \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_ROOT_PATH=/api

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY run.sh ./run.sh
RUN chmod +x ./run.sh

EXPOSE 8000

CMD ["./run.sh"]
