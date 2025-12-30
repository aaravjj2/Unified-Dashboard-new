FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir bentoml>=1.1.0 numpy pandas scikit-learn

COPY service.py .
COPY bentofile.yaml .

EXPOSE 3000

CMD ["bentoml", "serve", "service:PriceDirectionService", "--port", "3000", "--host", "0.0.0.0"]
