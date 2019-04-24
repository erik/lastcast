# Use an official Python runtime as a parent image
FROM python:3

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install lastcast along with any requirements
RUN python setup.py install

# Run lastcast when the container launches
CMD ["lastcast", "--config", "/lastcast.toml"]
