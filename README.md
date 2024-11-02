# GPT-Powered Meeting Assistant

This project demonstrates how to use OpenAI's GPT model and its function call feature to automate meeting scheduling, check user information, and manage availability in a database. It showcases how a language model (LLM) can be leveraged to automate common tasks while interacting with users in a natural, conversational manner.

## Overview

The Meeting Assistant is designed to:
- Create new meetings based on user input.
- Check existing users in the database and their availability.
- Use OpenAI's function calling feature to handle database transactions automatically.

The main goal of this project is to demonstrate how GPT models can be utilized to automate tasks and streamline communication with users by dynamically managing the flow of information, such as scheduling meetings and verifying availability, without manual intervention.

## Features

- Automates the process of scheduling meetings.
- Verifies user availability and checks existing data.
- Utilizes OpenAI's function calling feature to interact with a database.
- Provides a conversational interface for user interaction.
- Demonstrates a deployment process of GenAI project on AWS.

## OpenAI API and Function Calling Capabilities

MeetAssist uses OpenAI's API with function calling to automate meeting scheduling tasks. When a user request requires backend action (like retrieving or adding meetings), OpenAI’s API sends the request through ECS, which communicates with AWS Lambda to interact with the RDS database.

### Key Benefits

- **Automated Task Handling**: Natural language requests trigger backend actions, simplifying user interactions.
- **Efficient Communication**: OpenAI, ECS, and Lambda work together to process requests seamlessly.
- **Enhanced User Experience**: Users can make requests conversationally, improving ease of use.

## Deployment Architecture

The MeetAssist deployment utilizes a range of AWS services, ensuring high availability, scalability, and security:

1. **Amazon RDS**  
   Acts as the primary database for user and meeting data, storing information persistently and securely. RDS communicates with AWS Lambda, which retrieves and manages data as needed. The database used in this project is "MySQL".

2. **AWS Lambda**  
   The Lambda functions in MeetAssist handle the assistant requests as some API. After getting the request from ECS, it proceeds to fetching data from the database or creating new meeting. Lambda functions are invoked by an ECS task.

3. **Amazon ECS (Elastic Container Service) and ECR (Elastic Container Registry)**  
   ECS hosts the streamlit MeetAssist application in a Docker container. The streamlit app communicates with OpenAI API to get content from the user. When needed, the ECS sends to lambda API request to fetch data or update database. The container images are stored and versioned in Amazon ECR.

4. **Application Load Balancer (ALB)**  
   An Application Load Balancer routes traffic to the ECS task.

5. **Amazon Route 53**  
   MeetAssist is made publicly accessible through a domain managed by Route 53. The ALB is linked to this domain, giving users a simple, user-friendly URL to access the application. An ACM certificate is created for this domain name using AWS ACM.

6. **Terraform**  
   All AWS resources and infrastructure are managed with Terraform, enabling efficient deployment and consistent configuration. This infrastructure-as-code approach ensures that deployments are reproducible, maintainable, and easy to scale.

## Motivation

The project was developed to showcase how GPT models can be applied in real-world scenarios to automate database-driven tasks, particularly focusing on transaction automation (such as scheduling meetings) and natural language communication with users. It serves as an example of how AI can be integrated into business processes for efficiency.

## Technology Stack

- **OpenAI GPT (with function calling)**: Core engine for processing user input and automating tasks.
- **SQL**: Used to manage users and meeting data.
- **Python**: Main programming language for backend logic.
- **Streamlit**: The web application technology for fast deployment of Data Science projects.
- **AWS**: Terraform scripts using several AWS services.
