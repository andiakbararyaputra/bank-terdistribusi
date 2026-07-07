"""Jalankan seluruh sistem (3 node cabang + web gateway) dengan SATU perintah.

    python run_all.py

Browser terbuka otomatis ke dashboard. Tekan Ctrl+C untuk mematikan semuanya.
Untuk demo failover (mematikan satu cabang), jalankan node secara manual
di terminal terpisah — lihat README.md.
"""
import os
import subprocess
import sys
import time
import webbrowser

from common import config

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    if config.LAN_MODE:
        raise SystemExit(
            "network.json terdeteksi (mode multi-laptop).\n"
            "run_all.py hanya untuk mode satu komputer. Jalankan node per laptop:\n"
            "  python -m branch.main --name A   (di laptop cabang A, dst.)\n"
            "  python -m gateway.main           (di laptop gateway)\n"
            "Lihat README.md bagian 'Mode multi-laptop'.\n"
            "Untuk kembali ke mode lokal, hapus file network.json."
        )

    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    procs = []

    def start(nama, argv):
        p = subprocess.Popen([sys.executable, *argv], cwd=ROOT, env=env)
        procs.append((nama, p))

    print("=" * 62)
    print("  SISTEM BANK TERDISTRIBUSI — 3 node cabang + web gateway")
    print("=" * 62)

    for bid in config.BRANCHES:
        start(f"Cabang {bid}", ["-m", "branch.main", "--name", bid])
        time.sleep(0.4)  # beri jeda agar tiap cabang sempat sinkronisasi startup

    time.sleep(0.6)
    start("Gateway", ["-m", "gateway.main"])
    time.sleep(1.2)

    url = f"http://{config.GATEWAY_HOST}:{config.GATEWAY_PORT}"
    print()
    print(f">>> Dashboard: {url} (dibuka otomatis di browser)")
    print(">>> Tekan Ctrl+C untuk mematikan semua node.")
    print()
    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
            for item in list(procs):
                nama, p = item
                if p.poll() is not None:
                    print(f"[run_all] PERINGATAN: {nama} berhenti "
                          f"(exit code {p.returncode})")
                    procs.remove(item)
    except KeyboardInterrupt:
        print("\n[run_all] Mematikan semua node ...")
        for _, p in procs:
            p.terminate()
        for _, p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[run_all] Selesai.")


if __name__ == "__main__":
    main()
