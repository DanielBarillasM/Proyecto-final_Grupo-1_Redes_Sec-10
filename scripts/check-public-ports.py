from __future__ import annotations

import argparse
import datetime as dt
import socket
import sys

DEFAULT_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
                 1433, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017]


def probe(host: str, port: int, timeout: float) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return "abierto"
    except ConnectionRefusedError:
        return "cerrado"
    except (socket.timeout, TimeoutError, OSError):
        return "filtrado"
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("--expect-open", default="80", help="puertos que deben estar abiertos, separados por coma")
    parser.add_argument("--ports", default="", help="lista propia de puertos (por defecto, los comunes)")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    expected = {int(p) for p in args.expect_open.split(",") if p}
    ports = sorted({int(p) for p in args.ports.split(",") if p} | expected) if args.ports else sorted(set(DEFAULT_PORTS) | expected)
    print(f"# {dt.datetime.now().astimezone().isoformat(timespec='seconds')} destino={args.host} esperado_abierto={sorted(expected)}")
    print(f"{'PUERTO':>7}  {'OBTENIDO':<9} {'ESPERADO':<9} RESULTADO")
    failures = 0
    for port in ports:
        got = probe(args.host, port, args.timeout)
        want = "abierto" if port in expected else "no-abierto"
        ok = (got == "abierto") if port in expected else (got != "abierto")
        failures += not ok
        print(f"{port:>7}  {got:<9} {want:<9} {'OK' if ok else 'FALLA'}")
    print(f"\nResultado: {len(ports) - failures} conformes, {failures} no conformes")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
