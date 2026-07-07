"""Konfigurasi terpusat sistem bank terdistribusi (single source of truth).

Dipakai oleh modul branch, gateway, dan run_all agar definisi cabang,
port, dan lokasi data hanya ada di satu tempat.

MODE JARINGAN (multi-laptop, satu jaringan WiFi/LAN):
  Salin `network.example.json` menjadi `network.json`, isi IP tiap laptop,
  lalu salin file network.json YANG SAMA ke semua laptop. Jika file
  network.json ada, sistem otomatis masuk mode jaringan (server menerima
  koneksi dari komputer lain). Jika tidak ada, sistem berjalan mode lokal
  (semua node di satu komputer). Lihat README.md.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Direktori penyimpanan file JSON tiap cabang (dibuat otomatis saat pertama jalan)
DATA_DIR = ROOT / "data"

# File konfigurasi jaringan opsional (mode multi-laptop)
NETWORK_FILE = ROOT / "network.json"

# Definisi node cabang: id -> informasi node (default: mode lokal / satu komputer)
BRANCHES = {
    "A": {"nama": "Cabang A - Jakarta", "host": "127.0.0.1", "port": 8001},
    "B": {"nama": "Cabang B - Bandung", "host": "127.0.0.1", "port": 8002},
    "C": {"nama": "Cabang C - Surabaya", "host": "127.0.0.1", "port": 8003},
}

# Alamat web gateway (Flask)
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5000

# Mode jaringan aktif otomatis jika network.json ditemukan
LAN_MODE = NETWORK_FILE.exists()
if LAN_MODE:
    try:
        _net = json.loads(NETWORK_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"network.json tidak valid: {e}")
    for _bid, _info in _net.get("branches", {}).items():
        if _bid in BRANCHES:
            BRANCHES[_bid]["host"] = _info.get("host", BRANCHES[_bid]["host"])
            BRANCHES[_bid]["port"] = _info.get("port", BRANCHES[_bid]["port"])
    GATEWAY_HOST = _net.get("gateway", {}).get("host", GATEWAY_HOST)
    GATEWAY_PORT = _net.get("gateway", {}).get("port", GATEWAY_PORT)

# Alamat bind server:
# - mode lokal   : 127.0.0.1 (hanya bisa diakses dari komputer sendiri)
# - mode jaringan: 0.0.0.0   (menerima koneksi dari laptop lain di jaringan)
BIND_HOST = "0.0.0.0" if LAN_MODE else "127.0.0.1"

# Batas saldo maksimum, aman dari batas integer XML-RPC (2^31 - 1)
MAX_SALDO = 2_000_000_000


def rpc_url(branch_id: str) -> str:
    """URL server XML-RPC sebuah cabang."""
    info = BRANCHES[branch_id]
    return f"http://{info['host']}:{info['port']}"


def peers_of(branch_id: str) -> list:
    """Daftar id cabang lain (peer) dari sebuah cabang."""
    return [bid for bid in BRANCHES if bid != branch_id]


def branch_name(branch_id: str) -> str:
    """Nama lengkap sebuah cabang."""
    return BRANCHES[branch_id]["nama"]
