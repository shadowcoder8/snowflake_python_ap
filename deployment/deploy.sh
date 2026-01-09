#!/bin/bash

# Deployment Script for Oracle Linux (RHEL-based)
# Usage: ./deploy.sh

set -e

echo "----------------------------------------------------------------"
echo "❄️  Snowflake Python API Deployment Script for Oracle Linux"
echo "----------------------------------------------------------------"

# 1. Update System
echo "[1/6] Updating system packages..."
if command -v dnf &> /dev/null; then
    sudo dnf update -y
elif command -v yum &> /dev/null; then
    sudo yum update -y
elif command -v apt-get &> /dev/null; then
    sudo apt-get update -y
else
    echo "❌ Error: No supported package manager found (dnf, yum, or apt)."
    exit 1
fi

# 2. Install Git
if ! command -v git &> /dev/null; then
    echo "[2/6] Installing Git..."
    if command -v dnf &> /dev/null; then
        sudo dnf install -y git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    elif command -v apt-get &> /dev/null; then
        sudo apt-get install -y git
    fi
else
    echo "[2/6] Git is already installed."
fi

# 3. Install Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "[3/6] Installing Docker..."
    if command -v dnf &> /dev/null; then
        sudo dnf install -y dnf-plugins-core
        sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
        sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif command -v yum &> /dev/null; then
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif command -v apt-get &> /dev/null; then
        sudo apt-get install -y ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo \
          "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          \"$(. /etc/os-release && echo "$VERSION_CODENAME")\" stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
    
    sudo systemctl start docker
    sudo systemctl enable docker
    # Add current user to docker group
    sudo usermod -aG docker $USER
    echo "⚠️  Docker installed. You may need to log out and back in for group changes to take effect."
else
    echo "[3/6] Docker is already installed."
fi

# 4. Clone/Pull Repository
REPO_DIR="snowflake_python_api"
REPO_URL="https://github.com/your-username/snowflake-api.git" # REPLACE THIS WITH YOUR REPO URL

if [ -d "$REPO_DIR" ]; then
    echo "[4/6] Repository exists. Pulling latest changes..."
    cd $REPO_DIR
    git pull
else
    echo "[4/6] Cloning repository..."
    # If you are running this from the repo itself, just use current dir
    if [ -f "docker-compose.prod.yml" ]; then
        echo "Already inside the repository."
    else
        git clone $REPO_URL $REPO_DIR
        cd $REPO_DIR
    fi
fi

# 5. Setup Environment Variables
if [ ! -f ".env" ]; then
    echo "[5/6] Creating .env file..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Please edit .env file with your Snowflake credentials before running the app!"
    echo "   Run: nano .env"
    read -p "Press Enter to continue after you have edited the file (or to skip if you'll do it later)..."
else
    echo "[5/6] .env file already exists."
fi

# 6. Start Application
echo "[6/6] Starting application with Docker Compose..."
docker compose -f docker-compose.prod.yml up -d --build

echo "----------------------------------------------------------------"
echo "✅ Deployment Complete!"
echo "   API is running on port 8000"
echo "   Nginx is running on port 80 and 443"
echo "   Check logs with: docker compose -f docker-compose.prod.yml logs -f"
echo "----------------------------------------------------------------"
