#!/bin/bash
set -e
echo "========================================="
echo "  AirSense Platform Setup"
echo "========================================="

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo "Docker not found. Install from https://get.docker.com"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "docker-compose not found."; exit 1; }

# Setup env
if [ ! -f .env ]; then
  cp .env.example .env
  # Generate secrets
  JWT=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  FERNET=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "base64_key_here")
  sed -i "s/generate-a-secure-256bit-secret-here/$JWT/" .env
  sed -i "s/your_fernet_key/$FERNET/" .env
  echo "✓ .env created. Add your API keys before starting."
fi

chmod +x db/multi_db.sh

# Create SSL placeholder
mkdir -p nginx/ssl
if [ ! -f nginx/ssl/fullchain.pem ]; then
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/privkey.pem \
    -out nginx/ssl/fullchain.pem \
    -subj "/C=PK/ST=Punjab/L=Lahore/O=AirSense/CN=localhost" 2>/dev/null
  echo "✓ Self-signed SSL cert created (replace with Let's Encrypt in production)"
fi

echo "✓ Setup complete. Run: docker-compose up -d"
