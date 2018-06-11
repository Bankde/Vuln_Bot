# Use an official Python runtime as a parent image
FROM python:2.7-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environemnt variable
ENV LINE_CHANNEL_SECRET 	{LINE_CHANNEL_SECRET}
ENV LINE_CHANNEL_ACCESS_TOKEN 	{LINE_CHANNEL_ACCESS_TOKEN}
ENV ADMIN_PASSWORD		{ADMIN_PASSWORD}

# Run manage.py when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:8000", "manage:app"]
