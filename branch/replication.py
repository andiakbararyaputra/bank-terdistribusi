"""Replikasi data antar node cabang via XML-RPC (best-effort).

Konsep sistem terdistribusi yang didemonstrasikan:
- Replikasi: setiap transaksi disebarkan ke semua peer agar data konsisten.
- Toleransi kegagalan: peer yang mati dilewati tanpa menggagalkan transaksi.
- Sinkronisasi ulang: node yang baru hidup mengambil state terbaru dari peer.
"""
import xmlrpc.client

from common import config

RPC_ERRORS = (ConnectionError, OSError, xmlrpc.client.Error)


def urutan_state(state):
    """Kunci pengurutan state untuk replikasi: (version, origin).

    Origin (id cabang yang terakhir menulis) menjadi pemutus seri deterministik
    ketika dua cabang mencapai version yang sama akibat transaksi bersamaan,
    sehingga semua node tetap konvergen ke satu state.
    """
    return (state.get("version", 0), str(state.get("origin", "")))


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
            if terbaik is None or urutan_state(snap) > urutan_state(terbaik):
                terbaik = snap
        except RPC_ERRORS:
            continue
    return terbaik
