#!/usr/bin/env python3
"""Consulta DNS mínima (sustituto de dig) usando solo la biblioteca estándar.

Las EC2 privadas no tienen bind-utils ni salida a Internet para instalarlo. Este
script consulta un servidor concreto y sirve tanto para pruebas positivas
(Ventas/TI/Administración) como negativas (Visitas debe agotar el tiempo).

Uso:
    python3 dnsquery.py rrhh.rednova.internal            # servidor 10.10.0.164
    python3 dnsquery.py rrhh.rednova.internal 10.10.0.164 --type A
    python3 dnsquery.py 165.0.10.10.in-addr.arpa --type PTR

Código de salida: 0 con respuesta, 1 sin respuesta o error, 2 tiempo agotado.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import socket
import struct
import sys
import time

TYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12}
TYPE_NAMES = {v: k for k, v in TYPES.items()}
RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED"}


def encode_name(name: str) -> bytes:
    out = b""
    for label in name.rstrip(".").split("."):
        out += bytes([len(label)]) + label.encode("ascii")
    return out + b"\x00"


def read_name(data: bytes, offset: int) -> tuple[str, int]:
    labels, jumped, end = [], False, offset
    for _ in range(128):
        length = data[offset]
        if length & 0xC0 == 0xC0:
            if not jumped:
                end = offset + 2
            offset = ((length & 0x3F) << 8) | data[offset + 1]
            jumped = True
            continue
        if length == 0:
            if not jumped:
                end = offset + 1
            break
        labels.append(data[offset + 1 : offset + 1 + length].decode("ascii"))
        offset += 1 + length
    return ".".join(labels) + ".", end


def query(name: str, server: str, qtype: int, timeout: float, port: int = 53) -> int:
    qid = random.randint(0, 0xFFFF)
    packet = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0) + encode_name(name) + struct.pack(">HH", qtype, 1)
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"; fecha={stamp} origen={socket.gethostname()} servidor={server} consulta={name} {TYPE_NAMES[qtype]}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    start = time.monotonic()
    try:
        sock.sendto(packet, (server, port))
        data, _ = sock.recvfrom(4096)
    except socket.timeout:
        print(f"; RESULTADO: tiempo agotado ({timeout:.0f} s) - sin respuesta del servidor")
        return 2
    except OSError as exc:
        print(f"; RESULTADO: error de red: {exc}")
        return 1
    finally:
        sock.close()

    elapsed = (time.monotonic() - start) * 1000
    rid, flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", data[:12])
    rcode = flags & 0x000F
    aa = bool(flags & 0x0400)
    print(f"; status={RCODES.get(rcode, rcode)} autoritativa={'si' if aa else 'no'} respuestas={an} tiempo={elapsed:.1f} ms")
    if rid != qid:
        print("; RESULTADO: identificador de respuesta no coincide")
        return 1

    offset = 12
    for _ in range(qd):
        _, offset = read_name(data, offset)
        offset += 4
    for _ in range(an):
        rname, offset = read_name(data, offset)
        rtype, _rclass, ttl, rdlen = struct.unpack(">HHIH", data[offset : offset + 10])
        offset += 10
        rdata = data[offset : offset + rdlen]
        if rtype == 1:
            value = socket.inet_ntoa(rdata)
        elif rtype in (2, 5, 12):
            value, _ = read_name(data, offset)
        else:
            value = rdata.hex()
        offset += rdlen
        print(f"{rname}\t{ttl}\tIN\t{TYPE_NAMES.get(rtype, rtype)}\t{value}")

    return 0 if rcode == 0 and an > 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name")
    parser.add_argument("server", nargs="?", default="10.10.0.164")
    parser.add_argument("--type", default="A", choices=sorted(TYPES))
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--port", type=int, default=53)
    args = parser.parse_args()
    return query(args.name, args.server, TYPES[args.type], args.timeout, args.port)


if __name__ == "__main__":
    sys.exit(main())
