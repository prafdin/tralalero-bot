# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the bot will use (optional, for debugging purposes)
EXPOSE 8080

# Set environment variables (optional, adjust as needed)
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "main.py"]