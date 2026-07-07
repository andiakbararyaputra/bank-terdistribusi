"""Logika bisnis rekening bank pada satu node cabang (thread-safe)."""
import copy
import threading
from datetime import datetime

from branch import storage
from common import config

MAX_HISTORY = 50  # riwayat transaksi yang disimpan


def rp(n):
    """Format angka menjadi 'Rp1.000.000'."""
    return "Rp" + f"{int(n):,}".replace(",", ".")


class Bank:
    """State rekening + riwayat satu cabang, dengan lock untuk akses paralel."""

    def __init__(self, branch_id):
        self.branch_id = branch_id
        self.nama_cabang = config.branch_name(branch_id)
        self._lock = threading.Lock()
        self.state = storage.load(branch_id)

    def log(self, pesan):
        print(f"[{self.nama_cabang}] {pesan}", flush=True)

    # ---------------- operasi baca ----------------

    def ping(self):
        """Cek apakah node hidup (dipakai gateway untuk status)."""
        return True

    def get_accounts(self):
        with self._lock:
            return copy.deepcopy(self.state["accounts"])

    def get_balance(self, no_rek):
        no_rek = str(no_rek)
        with self._lock:
            acc = self.state["accounts"].get(no_rek)
            if acc is None:
                return {"ok": False, "pesan": f"Rekening {no_rek} tidak ditemukan."}
            return {"ok": True, "nama": acc["nama"], "saldo": acc["saldo"]}

    def get_history(self):
        with self._lock:
            return copy.deepcopy(self.state["history"])

    def snapshot(self):
        """Salinan lengkap state — dipakai untuk replikasi & sinkronisasi."""
        with self._lock:
            return copy.deepcopy(self.state)

    # ---------------- operasi tulis ----------------

    def deposit(self, no_rek, jumlah):
        no_rek = str(no_rek)
        with self._lock:
            galat = self._validasi(no_rek, jumlah)
            if galat:
                return galat
            acc = self.state["accounts"][no_rek]
            if acc["saldo"] + jumlah > config.MAX_SALDO:
                return {"ok": False, "pesan": "Setoran melebihi batas maksimum saldo."}
            acc["saldo"] += jumlah
            self._commit("SETOR", f"Setor {rp(jumlah)} ke {no_rek} ({acc['nama']})")
            self.log(f"SETOR {rp(jumlah)} -> rek {no_rek}, saldo kini {rp(acc['saldo'])}")
            return {
                "ok": True,
                "pesan": (f"Setor {rp(jumlah)} ke rekening {no_rek} ({acc['nama']}) "
                          f"berhasil. Saldo sekarang {rp(acc['saldo'])}."),
                "saldo": acc["saldo"],
            }

    def withdraw(self, no_rek, jumlah):
        no_rek = str(no_rek)
        with self._lock:
            galat = self._validasi(no_rek, jumlah)
            if galat:
                return galat
            acc = self.state["accounts"][no_rek]
            if jumlah > acc["saldo"]:
                return {"ok": False,
                        "pesan": f"Saldo tidak cukup. Saldo rekening {no_rek} "
                                 f"saat ini {rp(acc['saldo'])}."}
            acc["saldo"] -= jumlah
            self._commit("TARIK", f"Tarik {rp(jumlah)} dari {no_rek} ({acc['nama']})")
            self.log(f"TARIK {rp(jumlah)} <- rek {no_rek}, saldo kini {rp(acc['saldo'])}")
            return {
                "ok": True,
                "pesan": (f"Tarik {rp(jumlah)} dari rekening {no_rek} ({acc['nama']}) "
                          f"berhasil. Saldo sekarang {rp(acc['saldo'])}."),
                "saldo": acc["saldo"],
            }

    def transfer(self, dari, ke, jumlah):
        dari, ke = str(dari), str(ke)
        with self._lock:
            galat = self._validasi(dari, jumlah) or self._validasi(ke, jumlah)
            if galat:
                return galat
            if dari == ke:
                return {"ok": False, "pesan": "Rekening asal dan tujuan tidak boleh sama."}
            asal = self.state["accounts"][dari]
            tujuan = self.state["accounts"][ke]
            if jumlah > asal["saldo"]:
                return {"ok": False,
                        "pesan": f"Saldo tidak cukup. Saldo rekening {dari} "
                                 f"saat ini {rp(asal['saldo'])}."}
            if tujuan["saldo"] + jumlah > config.MAX_SALDO:
                return {"ok": False, "pesan": "Transfer melebihi batas maksimum saldo tujuan."}
            asal["saldo"] -= jumlah
            tujuan["saldo"] += jumlah
            self._commit("TRANSFER",
                         f"Transfer {rp(jumlah)} dari {dari} ({asal['nama']}) "
                         f"ke {ke} ({tujuan['nama']})")
            self.log(f"TRANSFER {rp(jumlah)} rek {dari} -> rek {ke}")
            return {
                "ok": True,
                "pesan": (f"Transfer {rp(jumlah)} dari {dari} ({asal['nama']}) "
                          f"ke {ke} ({tujuan['nama']}) berhasil."),
                "saldo": asal["saldo"],
            }

    # ---------------- replikasi ----------------

    def apply_replica(self, snapshot):
        """Terima state dari peer; terapkan hanya jika lebih baru (version lebih tinggi)."""
        with self._lock:
            if snapshot["version"] > self.state["version"]:
                self.state = snapshot
                storage.save(self.branch_id, self.state)
                self.log(f"REPLIKASI diterima (version {snapshot['version']})")
                return True
            return False

    # ---------------- helper internal ----------------

    def _validasi(self, no_rek, jumlah):
        """Validasi dasar; kembalikan dict galat atau None jika valid."""
        if no_rek not in self.state["accounts"]:
            return {"ok": False, "pesan": f"Rekening {no_rek} tidak ditemukan."}
        if not isinstance(jumlah, int) or isinstance(jumlah, bool) or jumlah <= 0:
            return {"ok": False, "pesan": "Jumlah harus bilangan bulat positif."}
        return None

    def _commit(self, jenis, keterangan):
        """Naikkan version, catat riwayat, simpan ke disk (dipanggil saat memegang lock)."""
        self.state["version"] += 1
        self.state["history"].insert(0, {
            "waktu": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "cabang": self.nama_cabang,
            "jenis": jenis,
            "keterangan": keterangan,
        })
        del self.state["history"][MAX_HISTORY:]
        storage.save(self.branch_id, self.state)
