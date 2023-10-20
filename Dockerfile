# Use an official Python runtime as a parent image
FROM python:3.8

# Just me ;)
MAINTAINER FreakErn <github-contact@freakern.de>

# Create a working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Run the Python script when the container launches
CMD ["python", "tibber2mqtt.py"]