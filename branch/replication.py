"""Replikasi data antar node cabang via XML-RPC (best-effort).

Konsep sistem terdistribusi yang didemonstrasikan:
- Replikasi: setiap transaksi disebarkan ke semua peer agar data konsisten.
- Toleransi kegagalan: peer yang mati dilewati tanpa menggagalkan transaksi.
- Sinkronisasi ulang: node yang baru hidup mengambil state terbaru dari peer.
"""
import xmlrpc.client

from common import config

RPC_ERRORS = (ConnectionError, OSError, xmlrpc.client.Error)


def _proxy(branch_id):
    return xmlrpc.client.ServerProxy(config.rpc_url(branch_id), allow_none=True)


def broadcast(branch_id, snapshot):
    """Kirim snapshot state terbaru ke semua peer. Peer mati dilewati.

    Mengembalikan daftar peer yang berhasil menerima replikasi.
    """
    terkirim = []
    for peer in config.peers_of(branch_id):
        try:
            _proxy(peer).replicate(snapshot)
            terkirim.append(peer)
        except RPC_ERRORS:
            pass  # best-effort: peer mati akan sinkron ulang saat hidup kembali
    return terkirim


def sync_from_peers(branch_id):
    """Ambil snapshot ber-version tertinggi dari peer yang hidup (saat startup)."""
    terbaik = None
    for peer in config.peers_of(branch_id):
        try:
            snap = _proxy(peer).snapshot()
            if terbaik is None or snap["version"] > terbaik["version"]:
                terbaik = snap
        except RPC_ERRORS:
            continue
    return terbaik
