# Use a lightweight Python image
FROM python:3.10-slim

# Avoid prompts during apt-get installs
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for Selenium and Chromium
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unzip \
    wget \
    chromium-driver \
    chromium \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxrandr2 \
    libappindicator1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Environment variables for Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy the app files into the container
COPY . .

# Install Python packages
