"""Server XML-RPC node cabang: mendaftarkan fungsi yang bisa dipanggil remote."""
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer

from branch import replication
from common import config


class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    """Server RPC multi-thread agar replikasi antar node tidak saling menunggu."""

    daemon_threads = True
    allow_reuse_address = True


def create_server(bank):
    """Buat server RPC untuk sebuah objek Bank dan daftarkan semua fungsinya."""
    info = config.BRANCHES[bank.branch_id]
    # Bind ke BIND_HOST: 127.0.0.1 (mode lokal) atau 0.0.0.0 (mode jaringan,
    # agar bisa diakses laptop lain di jaringan yang sama)
    server = ThreadedXMLRPCServer(
        (config.BIND_HOST, info["port"]), allow_none=True, logRequests=False
    )

    def tulis(fn, *args):
        """Jalankan operasi tulis, lalu replikasikan state baru ke semua peer."""
        hasil = fn(*args)
        if hasil.get("ok"):
            terkirim = replication.broadcast(bank.branch_id, bank.snapshot())
            if terkirim:
                bank.log(f"Replikasi terkirim ke peer: {', '.join(terkirim)}")
        return hasil

    # Operasi baca
    server.register_function(bank.ping, "ping")
    server.register_function(bank.get_accounts, "get_accounts")
    server.register_function(bank.get_balance, "get_balance")
    server.register_function(bank.get_history, "get_history")
    server.register_function(bank.snapshot, "snapshot")

    # Replikasi (dipanggil oleh peer)
    server.register_function(bank.apply_replica, "replicate")

    # Operasi tulis (otomatis memicu replikasi jika berhasil)
    server.register_function(lambda no, jml: tulis(bank.deposit, no, jml), "deposit")
    server.register_function(lambda no, jml: tulis(bank.withdraw, no, jml), "withdraw")
    server.register_function(
        lambda dari, ke, jml: tulis(bank.transfer, dari, ke, jml), "transfer"
    )
    return server
