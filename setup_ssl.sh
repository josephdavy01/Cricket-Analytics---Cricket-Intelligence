#!/bin/bash
set -e

echo "=========================================================="
echo "🔒 Enabling Free HTTPS / SSL with Let's Encrypt & Certbot"
echo "=========================================================="

DOMAIN="13-61-17-56.sslip.io"
EMAIL="josephdavy01@gmail.com"

echo "=== 1. Pulling Latest Code & Updating Django CSRF ==="
cd /home/ubuntu/cricket
git pull origin main || true
sudo systemctl restart django

echo "=== 2. Installing Certbot for Nginx ==="
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx

echo "=== 3. Updating Nginx Configuration for Domain ==="
sudo tee /etc/nginx/sites-available/cricket > /dev/null << NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $DOMAIN 13.61.17.56.sslip.io _;

    location /static/ {
        alias /home/ubuntu/cricket/frontend/staticfiles/;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

sudo nginx -t
sudo systemctl reload nginx

echo "=== 4. Requesting Official Let's Encrypt SSL Certificate ==="
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL --redirect

echo "=== 5. Reloading Nginx with SSL ==="
sudo systemctl reload nginx

echo "=========================================================="
echo "🎉 SUCCESS! Your site is now LIVE with HTTPS:"
echo "👉 https://$DOMAIN/"
echo "=========================================================="
