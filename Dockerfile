FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
COPY unobot/requirements.txt /tmp/uno-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r /tmp/uno-requirements.txt

COPY . .

CMD ["python", "main.py"]
