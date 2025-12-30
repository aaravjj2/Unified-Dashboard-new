FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir bentoml>=1.1.0 numpy

COPY service.py .
COPY bentofile.yaml .

EXPOSE 3000

CMD ["bentoml", "serve", "service:SentimentService", "--port", "3000", "--host", "0.0.0.0"]
