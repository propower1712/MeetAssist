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

## Deployment Architecture

The MeetAssist deployment utilizes a range of AWS services, ensuring high availability, scalability, and security:

1. **Amazon RDS**  
   Acts as the primary database for user and meeting data, storing information persistently and securely. RDS communicates with AWS Lambda, which retrieves and manages data as needed.

2. **AWS Lambda**  
   The Lambda functions in MeetAssist handle the core scheduling logic and process user requests. Lambda functions are invoked by ECS tasks, making it a scalable, cost-efficient backend component.

3. **Amazon ECS (Elastic Container Service) and ECR (Elastic Container Registry)**  
   ECS hosts the MeetAssist application in a Docker container, ensuring seamless deployment and scaling. The container images are stored and versioned in Amazon ECR, allowing for smooth updates to the ECS service.

4. **Application Load Balancer (ALB)**  
   An Application Load Balancer routes traffic to the ECS tasks, distributing requests evenly and ensuring reliable access for users. The ALB provides a stable endpoint for MeetAssist, helping to balance the load and maintain availability.

5. **Amazon Route 53**  
   MeetAssist is made publicly accessible through a domain managed by Route 53. The ALB is linked to this domain, giving users a simple, user-friendly URL to access the application.

6. **Terraform**  
   All AWS resources and infrastructure are managed with Terraform, enabling efficient deployment and consistent configuration. This infrastructure-as-code approach ensures that deployments are reproducible, maintainable, and easy to scale.

## Motivation

The project was developed to showcase how GPT models can be applied in real-world scenarios to automate database-driven tasks, particularly focusing on transaction automation (such as scheduling meetings) and natural language communication with users. It serves as an example of how AI can be integrated into business processes for efficiency.

## Technology Stack

- **OpenAI GPT (with function calling)**: Core engine for processing user input and automating tasks.
- **SQL**: Used to manage users and meeting data.
- **Python**: Main programming language for backend logic.
- **AWS**: Terraform scripts using several AWS services.
