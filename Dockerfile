FROM python:3.10-slim

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl unzip gnupg wget \
    chromium-driver chromium \
    libglib2.0-0 libnss3 libgconf-2-4 libxss1 libappindicator1 libindicator7 \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libgtk-3-0 libx11-xcb1 xvfb

# Install Python requirements
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . /app

# Expose the Streamlit port
EXPOSE 8501

CMD ["streamlit", "run", "selenium_enrich.py", "--server.port=8501", "--server.address=0.0.0.0"]
