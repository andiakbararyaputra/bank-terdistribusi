"""Klien RPC gateway -> node cabang, dengan failover otomatis.

Konsep sistem terdistribusi yang didemonstrasikan:
- RPC: gateway memanggil fungsi remote pada node cabang.
- Failover: jika cabang pilihan mati, permintaan otomatis dialihkan
  ke cabang lain yang hidup (mungkin karena semua data tereplikasi).
"""
import xmlrpc.client

from common import config

RPC_ERRORS = (ConnectionError, OSError, xmlrpc.client.Error)


class SemuaCabangMati(Exception):
    """Dilempar ketika tidak ada satu pun cabang yang bisa dihubungi."""


def _proxy(branch_id):
    return xmlrpc.client.ServerProxy(config.rpc_url(branch_id), allow_none=True)


def call_branch(branch_id, method, *args):
    """Panggil fungsi RPC pada cabang pilihan, failover ke cabang lain jika mati.

    Mengembalikan tuple (hasil, id_cabang_yang_melayani).
    """
    urutan = [branch_id] + [b for b in config.BRANCHES if b != branch_id]
    for bid in urutan:
        try:
            hasil = getattr(_proxy(bid), method)(*args)
            return hasil, bid
        except RPC_ERRORS:
            continue
    raise SemuaCabangMati("Semua cabang tidak dapat dihubungi.")


def branches_status():
    """Cek cabang mana saja yang hidup: {id_cabang: True/False}."""
    status = {}
    for bid in config.BRANCHES:
        try:
            _proxy(bid).ping()
            status[bid] = True
        except RPC_ERRORS:
            status[bid] = False
    return status
