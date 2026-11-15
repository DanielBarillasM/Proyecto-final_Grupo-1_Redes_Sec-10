
set -euo pipefail
exec > >(tee -a /var/log/rednova-hardening.log) 2>&1

WEB=0
HTTPS=off
while [ $# -gt 0 ]; do
  case "$1" in
    --web)   WEB=1 ;;
    --https) shift; HTTPS="${1:-off}" ;;
    *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
  esac
  shift
done
ADMIN_NET="10.10.0.176/28"  
echo "[$(date -Is)] Hardening: web=$WEB https=$HTTPS"

cat > /etc/ssh/sshd_config.d/90-rednova.conf <<'CONF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
AllowTcpForwarding no
CONF
sshd -t && systemctl reload sshd

cat > /etc/sysctl.d/90-rednova.conf <<'CONF'
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv6.conf.all.accept_redirects = 0
CONF
sysctl --system >/dev/null

for svc in postfix rpcbind cups avahi-daemon telnet.socket; do
  if systemctl list-unit-files "$svc*" 2>/dev/null | grep -q "$svc"; then
    systemctl disable --now "$svc" 2>/dev/null || true
    echo "Servicio deshabilitado: $svc"
  fi
done

if [ "$WEB" -eq 1 ]; then
  if [ -d /usr/share/nginx/html ]; then
    chown -R root:root /usr/share/nginx/html
    find /usr/share/nginx/html -type d -exec chmod 0755 {} +
    find /usr/share/nginx/html -type f -exec chmod 0644 {} +
  fi
  chmod 0750 /etc/nginx 2>/dev/null || true
fi


PORTS=""
if [ "$WEB" -eq 1 ]; then
  PORTS="80"
  [ "$HTTPS" = "on" ] && PORTS="80, 443"
fi
install -d -m 0755 /etc/nftables
{
  echo 'flush ruleset'
  echo 'table inet rednova {'
  echo '  chain input {'
  echo '    type filter hook input priority 0; policy drop;'
  echo '    iif "lo" accept'
  echo '    ct state established,related accept'
  echo '    ct state invalid drop'
  echo '    icmp type echo-request limit rate 5/second accept'
  echo "    ip saddr $ADMIN_NET tcp dport 22 accept"
  [ -n "$PORTS" ] && echo "    tcp dport { $PORTS } accept"
  echo '  }'
  echo '  chain forward { type filter hook forward priority 0; policy drop; }'
  echo '  chain output  { type filter hook output priority 0; policy accept; }'
  echo '}'
} > /etc/nftables/rednova.nft
chmod 0600 /etc/nftables/rednova.nft

if nft -c -f /etc/nftables/rednova.nft; then
  echo 'include "/etc/nftables/rednova.nft"' > /etc/sysconfig/nftables.conf
  systemctl enable nftables
  nft -f /etc/nftables/rednova.nft
  echo "nftables activo: SSH desde $ADMIN_NET${PORTS:+, TCP $PORTS públicos}"
else
  echo "ADVERTENCIA: la regla nftables no validó; el firewall del SO no se aplicó" >&2
fi

echo "[$(date -Is)] Hardening completado"
