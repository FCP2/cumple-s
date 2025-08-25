FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg unzip \
    libnss3 libatk-bridge2.0-0 libxkbcommon0 libgbm1 libgtk-3-0 libasound2 \
    fonts-liberation \
  && rm -rf /var/lib/apt/lists/*

# Google Chrome estable
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub -o /etc/apt/keyrings/google-linux-signing-key.pub && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux-signing-key.pub] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y --no-install-recommends google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Chromedriver que coincide con el major de Chrome
RUN set -eux; \
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}'); \
    CHROME_MAJOR=${CHROME_VERSION%%.*}; \
    CHROMEDRIVER_VERSION=$(curl -fsSL "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR}"); \
    curl -fsSL -o /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"; \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/; \
    rm /tmp/chromedriver.zip; \
    chmod +x /usr/local/bin/chromedriver; \
    chromedriver --version

ENV PYTHONUNBUFFERED=1
ENV PORT=10000
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER=/usr/local/bin/chromedriver

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data && useradd -ms /bin/bash appuser && chown -R appuser:appuser /data /app
USER appuser

CMD ["python", "app.py"]
