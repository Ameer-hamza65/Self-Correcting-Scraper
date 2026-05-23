# Use the official Microsoft Playwright image which includes all chromium and system dependencies
FROM mcr.microsoft.com/playwright:v1.40.0-jammy

# Install Python requirements
RUN apt-get update && apt-get install -y python3-pip python3-venv

WORKDIR /app

# Copy requirements list and install python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy backend source files
COPY . .

# Expose backend port
EXPOSE 8000

# Start uvicorn server
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
