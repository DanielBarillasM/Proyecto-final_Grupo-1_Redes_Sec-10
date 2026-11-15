#!/bin/bash
# =============================================================================
# Sonda remota de la suite de Fase 2 (CC3067 - Grupo 1). Responsable: Genser Catalan
#
# test-phase2.ps1 la envia por stdin a la instancia de origen (ssh ... 'bash -s -- ...'),
# por lo que no necesita estar instalada en las EC2. Solo usa herramientas presentes en
# Amazon Linux 2023 sin paquetes extra: bash, timeout, ping, curl y getent.
# No modifica la instancia ni la red. Archivo en ASCII a proposito (stdin desde Windows).
#
# Uso:
#   bash phase2-probe.sh tcp     <host> <puerto> <timeout_s>
#   bash phase2-probe.sh icmp    <host> <timeout_s>
#   bash phase2-probe.sh http    <url> <timeout_s> [cabecera Host]
#   bash phase2-probe.sh resolve <nombre>
#
# La ultima linea siempre es  RESULTADO=<valor>  con uno de:
#   tcp:     abierto | rechazado | filtrado | sin_ruta | error
#   icmp:    respuesta | sin_respuesta | error
#   http:    http_<codigo> | filtrado | rechazado | dns_fallo | error
#   resolve: resuelto:<ip> | no_resuelto
# Exit code: 0 siempre que la sonda se ejecuto; el veredicto lo decide test-phase2.ps1.
# =============================================================================
set -uo pipefail

kind="${1:-}"
shift || true

src_ip="$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n1)"
echo "# fecha=$(date -Is) origen_host=$(hostname) origen_ip=${src_ip:-desconocida} sonda=${kind} args=$*"

case "$kind" in
  tcp)
    host="$1"; port="$2"; t="${3:-5}"
    echo "# comando: timeout ${t} bash -c 'exec 3<>/dev/tcp/${host}/${port}'"
    err="$(timeout "$t" bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>&1)"
    rc=$?
    [ -n "$err" ] && echo "$err"
    if   [ $rc -eq 0 ];   then r=abierto
    elif [ $rc -eq 124 ]; then r=filtrado
    elif echo "$err" | grep -qi 'refused';  then r=rechazado
    elif echo "$err" | grep -qi 'no route'; then r=sin_ruta
    else r=error
    fi
    echo "RESULTADO=$r"
    ;;
  icmp)
    host="$1"; t="${2:-5}"
    echo "# comando: ping -c 3 -W ${t} ${host}"
    ping -c 3 -W "$t" "$host" 2>&1
    rc=$?
    if   [ $rc -eq 0 ]; then echo "RESULTADO=respuesta"
    elif [ $rc -eq 1 ]; then echo "RESULTADO=sin_respuesta"
    else echo "RESULTADO=error"
    fi
    ;;
  http)
    url="$1"; t="${2:-5}"; hosthdr="${3:-}"
    args=(-sS -o /dev/null -w '%{http_code}' --connect-timeout "$t" --max-time "$((t * 2))")
    [ -n "$hosthdr" ] && args+=(-H "Host: ${hosthdr}")
    echo "# comando: curl ${args[*]} ${url}"
    code="$(curl "${args[@]}" "$url" 2>/tmp/rednova-probe-curl.err)"
    rc=$?
    cat /tmp/rednova-probe-curl.err 2>/dev/null; rm -f /tmp/rednova-probe-curl.err
    echo "curl_exit=${rc} http_code=${code:-000}"
    case $rc in
      0)  echo "RESULTADO=http_${code}" ;;
      6)  echo "RESULTADO=dns_fallo" ;;
      7)  echo "RESULTADO=rechazado" ;;
      28) echo "RESULTADO=filtrado" ;;
      *)  echo "RESULTADO=error" ;;
    esac
    ;;
  resolve)
    name="$1"
    echo "# comando: getent ahostsv4 ${name}"
    out="$(getent ahostsv4 "$name" 2>&1)"
    if [ -n "$out" ]; then
      echo "$out"
      echo "RESULTADO=resuelto:$(echo "$out" | awk 'NR==1{print $1}')"
    else
      echo "RESULTADO=no_resuelto"
    fi
    ;;
  *)
    echo "Sonda desconocida: '${kind}'. Use tcp, icmp, http o resolve." >&2
    echo "RESULTADO=error"
    ;;
esac
exit 0
