FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory and ensure it's writable
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port for the web service
EXPOSE 5000

# The command to run the application will be specified in docker-compose.yml
CMD ["python"]
