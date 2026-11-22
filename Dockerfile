FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1 DB_PATH=/data/records.db
EXPOSE 8000
CMD ["python", "-m", "app.main"]
