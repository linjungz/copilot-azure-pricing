# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app
COPY price_api_response/* /app/price_api_response/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Expose the port that the Streamlit will run on
EXPOSE 8501

# Run the command to start the streamlit app
CMD ["streamlit", "run", "app.py"]