# Use the official Python image as the base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements file to the container
COPY requirements.txt ./
COPY requirements_lambda.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements_lambda.txt

# Create utils directory
RUN mkdir utils
RUN mkdir resources

# Copy the Streamlit app code into the container
COPY app.py .
COPY utils/__init__.py utils
COPY utils/helpers.py utils
COPY utils/constants.py utils
COPY utils/meetings_api_lambda.py utils
COPY resources/* resources

# Expose the port Streamlit runs on
EXPOSE 8501

# Set Streamlit configuration (optional)
ENV STREAMLIT_SERVER_HEADLESS=true

# Command to run the app
CMD ["streamlit", "run", "app.py"]

# ~/start-docker.sh
# docker build -t meet_assist_img .
# docker run -e FUNCTION_NAME=$(terraform output -raw lambda_function_arn) -e OPENAI_API_KEY=$(jq -r '.OPENAI_API_KEY' config.json) -p 8501:8501 -v ~/.aws:/root/.aws 211125691730.dkr.ecr.us-east-1.amazonaws.com/meet-assist-repo:latest