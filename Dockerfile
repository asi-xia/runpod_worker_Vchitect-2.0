# Stage 1: Base image with common dependencies
ARG NV_VERSION=12.4.1-cudnn-runtime-ubuntu22.04
FROM nvidia/cuda:${NV_VERSION}

# Prevents prompts from packages asking for user input during installation
ENV DEBIAN_FRONTEND=noninteractive
# Prefer binary wheels over source distributions for faster pip installations
ENV PIP_PREFER_BINARY=1
# Ensures output from python is printed immediately to the terminal without buffering
ENV PYTHONUNBUFFERED=1 
# Speed up some cmake builds
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

RUN apt update && apt install software-properties-common -y \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && add-apt-repository ppa:ubuntuhandbook1/ffmpeg6 -y \
    && apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev pkg-config -y

# Install Python, git and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.11-dev \
    python3-pip \
    python3-apt \
    git \
    git-lfs \
    libgl1 \
    ffmpeg \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/pip3 /usr/bin/pip \
    && python -m pip install --upgrade pip \
    && git lfs install

# Clean up to reduce image size
# RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install runpod and clone VchitectXL
RUN pip install huggingface_hub runpod requests shortuuid \
    && pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu124 \
    && git clone https://github.com/asi-xia/Vchitect-2.0.git

# Change working directory to Vchitect-2.0
WORKDIR /Vchitect-2.0
ADD src/rp_handler.py ./
ARG BUILD_TYPE=code

RUN --mount=type=secret,id=hf_token,mode=0444,required=true \
    huggingface-cli login --token $(cat /run/secrets/hf_token) \
    && pip install -r requirements.txt

RUN if [ "$BUILD_TYPE" = "full" ]; then \
        huggingface-cli download --resume-download Vchitect/Vchitect-2.0-2B --local-dir pretrained_weights; \
    fi

# Go back to the root
WORKDIR /

# Add scripts
ADD src/start.sh ./
RUN chmod +x /start.sh \
    && sed -i 's/\r$//' /start.sh

# Start container
CMD ["/start.sh"]
