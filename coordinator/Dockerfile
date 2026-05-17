# Use official Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first — this way Docker caches the pip install step
# and only re-runs it if requirements.txt changes, not on every code change
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the REST API port
EXPOSE 8000

# Start the FastAPI app with uvicorn
# --host 0.0.0.0 makes it accessible from outside the container
# --reload is off in production — we'll control this via docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]