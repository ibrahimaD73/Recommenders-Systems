FROM python:3.9-slim

RUN apt-get update && apt-get install -y build-essential libssl-dev libffi-dev python3-dev
l
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000

EXPOSE 5000

CMD ["python", "app.py"]