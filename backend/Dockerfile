# Use the official Microsoft Playwright image which includes all chromium and system dependencies
FROM mcr.microsoft.com/playwright:v1.40.0-jammy

# Install Python requirements
RUN apt-get update && apt-get install -y python3-pip python3-venv

WORKDIR /app

# Copy requirements list and install python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy backend source files into a nested backend directory inside the container
COPY . ./backend

# Set the Python path to /app so that "import backend" resolves correctly
ENV PYTHONPATH=/app

# Expose backend port
EXPOSE 8000

# Start uvicorn server pointing to backend.main:app
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
