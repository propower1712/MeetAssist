#!/bin/bash

# Assign command line arguments to variables
REGION=$1
ECR_REPO_URL=$2

cd ..
# Build the docker image
docker build --no-cache -t meet_assist_img .

# Authenticate Docker to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO_URL

# Tag your Docker image
docker tag meet_assist_img:latest $ECR_REPO_URL:latest

# Push the image to ECR
docker push $ECR_REPO_URL:latest

cd terraform_scripts