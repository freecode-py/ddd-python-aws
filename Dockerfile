# Use the official Ubuntu image as the base image
FROM ubuntu:latest

# Avoid interactive prompts during the installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install necessary dependencies
RUN apt-get update && \
    apt-get install -y software-properties-common curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python 3.9 and pip
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.9 python3.9-distutils && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 && \
    curl -s https://bootstrap.pypa.io/get-pip.py | python3

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_14.x | bash - && \
    apt-get install -y nodejs

# Set the working directory

# Install Serverless Framework globally via npm
RUN npm install -g serverless
RUN npm config set unsafe-perm=true \
    && npm install -g serverless@3.33.0 \
    && npm install serverless-wsgi@3.0.2 \
    && npm install serverless-python-requirements@6.0.0 \
    && npm install npm install serverless-dynamodb-autoscaling@0.6.2\
    && npm install serverless-deployment-bucket --save-dev

# Install npm dependencies
RUN npm install

# Copy application code and requirements.txt to the container
COPY requirements.txt /tmp/requirements.txt
# Install Python project dependencies for local env
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

# COPY layers /tmp/layers
COPY . .
# RUN python3 -m pip install -t ./layers/commons -r /app/layers/commons/aws_requirements.txt





