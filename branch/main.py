"""Entry point node cabang.

Cara menjalankan (dari folder bank-terdistribusi):
    python -m branch.main --name A
"""
import argparse
import socket

from branch import replication
from branch.bank import Bank
from branch.server import create_server
from common import config


def main():
    parser = argparse.ArgumentParser(description="Node cabang bank terdistribusi")
    parser.add_argument(
        "--name", required=True, choices=list(config.BRANCHES),
        help="ID cabang yang dijalankan (A/B/C)",
    )
    args = parser.parse_args()

    # Timeout socket agar panggilan ke peer yang mati tidak menggantung
    socket.setdefaulttimeout(3)

    bank = Bank(args.name)

    # Sinkronisasi saat startup: ambil data terbaru dari peer yang hidup
    snap = replication.sync_from_peers(args.name)
    if snap and bank.apply_replica(snap):
        bank.log("Sinkronisasi startup dari peer berhasil.")

    server = create_server(bank)
    if config.LAN_MODE:
        bank.log("Mode jaringan (LAN) aktif — network.json terdeteksi, "
                 "node bisa diakses dari laptop lain.")
    bank.log(f"Node aktif di {config.rpc_url(args.name)} "
             f"| peers: {', '.join(config.peers_of(args.name))}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        bank.log("Node dimatikan.")


if __name__ == "__main__":
    main()
