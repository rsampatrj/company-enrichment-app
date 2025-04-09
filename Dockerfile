FROM python:3.10-slim

# Avoid prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg2 unzip curl xvfb libxi6 libgconf-2-4 libnss3 libxss1 libappindicator1 libindicator7 \
    fonts-liberation libatk-bridge2.0-0 libgtk-3-0 libdrm2 libgbm1 libasound2 libxshmfence1 libxrandr2 \
    libu2f-udev libvulkan1 libxdamage1 libxcomposite1 libxfixes3 \
    chromium chromium-driver && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/lib/chromium/chromedriver

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "selenium_enrich.py", "--server.port=8501", "--server.enableCORS=false"]
