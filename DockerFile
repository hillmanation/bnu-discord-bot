# Use the official Python Alpine image
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app

# Expose the port that the bot will use if necessary (optional)
# EXPOSE 8000

# Set the entry point to run the bot
CMD ["python", "main.py"]
