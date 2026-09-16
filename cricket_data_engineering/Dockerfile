FROM apache/airflow:3.3.1

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    xvfb \
    xauth \
    libcairo2 \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libasound2 \
    libxkbcommon0 \
    libdrm2 \
    libxcb1 \
    ca-certificates \
    fonts-liberation \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r /requirements.txt

RUN playwright install chromium