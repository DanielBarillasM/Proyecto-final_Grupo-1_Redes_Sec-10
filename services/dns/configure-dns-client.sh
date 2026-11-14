#!/usr/bin/env bash
# =============================================================================
# Configura un cliente interno para resolver *.rednova.internal con BIND9.
# Uso (en Ventas, TI, Administración o Data Center; requiere sudo):
#   sudo bash configure-dns-client.sh [IP_DNS]
# No ejecutar en Visitas ni DMZ.
# =============================================================================
set -euo pipefail

DNS_IP="${1:-10.10.0.164}"
DOMAIN="rednova.internal"
DROPIN_DIR="/etc/systemd/resolved.conf.d"
DROPIN="${DROPIN_DIR}/rednova-internal.conf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ejecute con sudo." >&2
  exit 1
fi

if systemctl is-active --quiet systemd-resolved; then
  install -d -m 0755 "${DROPIN_DIR}"
  cat > "${DROPIN}" <<EOF
[Resolve]
DNS=${DNS_IP}
Domains=~${DOMAIN} ~0.10.10.in-addr.arpa
EOF
  chmod 0644 "${DROPIN}"
  systemctl restart systemd-resolved
  echo "systemd-resolved: *.${DOMAIN} -> ${DNS_IP}"
  resolvectl status | sed -n '1,15p'
else
  # Respaldo: BIND9 también reenvía nombres externos, por lo que puede quedar
  # como primer servidor sin romper la resolución general.
  cp -n /etc/resolv.conf /etc/resolv.conf.rednova.bak
  { echo "nameserver ${DNS_IP}"; grep -v "^nameserver ${DNS_IP}$" /etc/resolv.conf.rednova.bak; } > /etc/resolv.conf
  echo "resolv.conf: ${DNS_IP} agregado como primer servidor"
fi

echo "--- Prueba ---"
getent hosts "rrhh.${DOMAIN}" || { echo "No se resolvió rrhh.${DOMAIN}" >&2; exit 2; }
