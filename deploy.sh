#!/bin/bash
set -e

echo "=========================================================="
echo "🚀 Starting Cricket Platform Automated Cloud Deployment..."
echo "=========================================================="

echo "=== 1. Setting up 2GB Swap Memory ==="
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap created successfully."
else
    echo "Swapfile already exists."
fi

echo "=== 2. Installing System Packages ==="
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    postgresql \
    postgresql-contrib \
    nginx \
    git \
    curl

echo "=== 3. Configuring PostgreSQL ==="
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -u postgres psql -c "CREATE DATABASE t20i_cricket_analytics;" || true
sudo -u postgres psql -c "CREATE USER cricket_admin WITH ENCRYPTED PASSWORD 'CricketPass2026!';" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE t20i_cricket_analytics TO cricket_admin;"
sudo -u postgres psql -c "ALTER DATABASE t20i_cricket_analytics OWNER TO cricket_admin;"

echo "=== 4. Cloning/Updating Codebase ==="
if [ -d "/home/ubuntu/cricket" ]; then
    cd /home/ubuntu/cricket && git pull origin main || true
else
    git clone https://github.com/josephdavy01/Cricket-Analytics---Cricket-Intelligence.git /home/ubuntu/cricket
fi
sudo chown -R ubuntu:ubuntu /home/ubuntu/cricket

echo "=== 5. Importing Database Dump ==="
PGPASSWORD='CricketPass2026!' psql -U cricket_admin -d t20i_cricket_analytics -h localhost -f /home/ubuntu/cricket/cricket_analytics.sql || true

echo "=== 6. Installing Standalone Python 3.11 via uv ==="
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11

echo "=== 7. Setting up FastAPI Backend with Python 3.11 ==="
cd /home/ubuntu/cricket/backend
rm -rf venv
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -r requirements.txt psycopg2-binary
deactivate

sudo tee /etc/systemd/system/fastapi.service > /dev/null << 'SERVICE'
[Unit]
Description=Cricket Analytics FastAPI Backend
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/cricket/backend
Environment="PATH=/home/ubuntu/cricket/backend/venv/bin"
Environment="DATABASE_URL=postgresql+asyncpg://cricket_admin:CricketPass2026!@localhost:5432/t20i_cricket_analytics"
ExecStart=/home/ubuntu/cricket/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

echo "=== 8. Setting up Django Frontend with Python 3.11 ==="
cd /home/ubuntu/cricket/frontend
rm -rf venv
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
deactivate

sudo tee /etc/systemd/system/django.service > /dev/null << 'SERVICE'
[Unit]
Description=Cricket Analytics Django Frontend
After=network.target fastapi.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/cricket/frontend
Environment="PATH=/home/ubuntu/cricket/frontend/venv/bin"
Environment="DEBUG=False"
Environment="ALLOWED_HOSTS=*"
Environment="FASTAPI_BASE_URL=http://127.0.0.1:8000"
Environment="SECRET_KEY=cricket-prod-secret-2026-xyz"
ExecStart=/home/ubuntu/cricket/frontend/venv/bin/gunicorn ipl_frontend.wsgi:application --bind 127.0.0.1:8001 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

echo "=== 9. Configuring Nginx ==="
sudo tee /etc/nginx/sites-available/cricket > /dev/null << 'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location /static/ {
        alias /home/ubuntu/cricket/frontend/staticfiles/;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/cricket /etc/nginx/sites-enabled/
sudo nginx -t

echo "=== 10. Starting and Enabling Services ==="
sudo systemctl daemon-reload
sudo systemctl enable fastapi django nginx
sudo systemctl restart fastapi django nginx

echo "=========================================================="
echo "🎉 Deployment Completed Successfully! Access at http://13.61.17.56/"
echo "=========================================================="
