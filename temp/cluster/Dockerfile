# Base image with Python installed
FROM ubuntu:20.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update system and install required packages, including Python
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev build-essential && \
    apt-get clean

RUN apt install git -y

# Set a working directory in the container
WORKDIR /app

# Copy project files into the container
COPY . /app

RUN git clone https://github.com/TimDettmers/bitsandbytes.git
RUN cd bitsandbytes
RUN python3 setup.py install
RUN cd ..

# Install dependencies
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# Expose any ports your app uses (optional)
EXPOSE 8000  

# Define the command to run the application
CMD ["python3", "Graph_Structuring/test.py"]  
