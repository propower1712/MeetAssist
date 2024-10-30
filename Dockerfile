# Use the official Python image as the base
FROM python:3.8-slim  # You can change the version as needed

# Set the working directory in the container
WORKDIR /app

# Copy requirements file to the container
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app code into the container
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8501

# Set Streamlit configuration (optional)
ENV STREAMLIT_SERVER_HEADLESS=true

# Command to run the app
CMD ["streamlit", "run", "app.py"]
