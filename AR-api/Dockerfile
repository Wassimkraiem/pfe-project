FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "app.app:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--workers", "2", "--bind", "0.0.0.0:8000", "--keep-alive", "65", "--timeout", "120", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]