set -euo pipefail
DOMAIN="${1:?Indique el dominio público}"
EMAIL="${2:?Indique un correo de contacto para Let Encrypt}"

# El dominio debe resolver a esta instancia; de lo contrario ACME fallará.
TOKEN=$(curl -s -m 5 -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
MYIP=$(curl -s -m 5 -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
DNSIP=$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}')
echo "IP pública de la instancia: $MYIP | $DOMAIN resuelve a: ${DNSIP:-nada}"
[ "$MYIP" = "$DNSIP" ] || { echo "El dominio aún no apunta a esta instancia; abortado." >&2; exit 1; }

dnf -y install augeas-libs python3-pip
python3 -m venv /opt/certbot
/opt/certbot/bin/pip install --quiet certbot certbot-nginx
/opt/certbot/bin/certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --no-eff-email \
  --redirect --non-interactive

# HSTS solo después de que HTTPS funciona.
if ! grep -q Strict-Transport-Security /etc/nginx/nginx.conf; then
  sed -i '0,/add_header X-Content-Type-Options/s//add_header Strict-Transport-Security "max-age=31536000" always;\n        add_header X-Content-Type-Options/' /etc/nginx/nginx.conf
fi
nginx -t && systemctl reload nginx

# Renovación automática.
echo '0 3 * * * root /opt/certbot/bin/certbot renew --quiet --post-hook "systemctl reload nginx"' > /etc/cron.d/certbot-renew
echo "HTTPS listo. Pruebe: curl -I http://$DOMAIN/ (debe redirigir) y curl -I https://$DOMAIN/"
