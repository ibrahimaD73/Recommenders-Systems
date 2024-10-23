FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/Recommenders-Systems

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .secrets ./.secrets

COPY . .

ENV PORT=6000
EXPOSE 6000

CMD ["python", "app.py"]
