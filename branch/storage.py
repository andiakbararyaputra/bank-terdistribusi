"""Persistensi data cabang ke file JSON + data awal (seed)."""
import json
import os

from common import config

# Rekening awal ketika sistem pertama kali dijalankan
SEED_ACCOUNTS = {
    "1001": {"nama": "Andi Akbar Arya Putra", "saldo": 500_000},
    "1002": {"nama": "Muh. As'ad Habib", "saldo": 750_000},
    "1003": {"nama": "Muhammad Pasyafatir", "saldo": 1_000_000},
}


def _file_path(branch_id):
    return config.DATA_DIR / f"data_{branch_id}.json"


def initial_state():
    """State awal: rekening seed, version 0, riwayat kosong."""
    return {
        "version": 0,
        "origin": "",  # id cabang penulis terakhir (pemutus seri replikasi)
        "accounts": json.loads(json.dumps(SEED_ACCOUNTS)),  # salinan bebas
        "history": [],
    }


def load(branch_id):
    """Muat state cabang dari file JSON; jika belum ada, pakai state awal."""
    path = _file_path(branch_id)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return initial_state()


def save(branch_id, state):
    """Simpan state cabang ke file JSON secara atomik (folder dibuat otomatis).

    Tulis ke file sementara lalu os.replace agar file data tidak pernah
    korup/separuh tertulis jika proses mati di tengah penyimpanan.
    """
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _file_path(branch_id)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
