# Sistem Bank Terdistribusi

Tugas Sistem Terdistribusi — simulasi bank dengan **3 node cabang** yang saling
tersinkronisasi, dibangun dengan Python.

| Konsep Sistem Terdistribusi | Implementasi                                                   |
| --------------------------- | -------------------------------------------------------------- |
| RPC (Remote Procedure Call) | XML-RPC antar node & gateway (modul`xmlrpc` bawaan Python)   |
| Microservices / REST-Web    | Web gateway Flask sebagai pintu masuk pengguna                 |
| Replikasi data              | Setiap transaksi disebarkan ke semua cabang (state + version)  |
| Fault tolerance / failover  | Gateway otomatis mengalihkan request ke cabang lain yang hidup |
| Sinkronisasi ulang          | Cabang yang baru hidup mengambil data terbaru dari peer        |

## Arsitektur

```
Browser ──HTTP──> Gateway Flask (port 5000)
                     │  XML-RPC (failover otomatis)
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Cabang A      Cabang B      Cabang C
  (RPC :8001)   (RPC :8002)   (RPC :8003)
  data_A.json   data_B.json   data_C.json
        └──── replikasi RPC antar peer ────┘
```

Dashboard web menampilkan kartu statistik (total saldo, jumlah rekening,
cabang aktif, transaksi tercatat), status tiap node (**AKTIF**/**MATI**),
daftar rekening, riwayat transaksi yang tereplikasi, serta cabang mana yang
sedang melayani data ("Data dilayani oleh Cabang X").

## Cara Menjalankan

### 1. Install dependensi (sekali saja)

```bash
pip install -r requirements.txt
```

> Jika muncul error *externally-managed-environment* (Ubuntu/Debian), gunakan
> virtual environment:
>
> ```bash
> python3 -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt
> ```

### 2. Jalankan semua dengan SATU perintah

```bash
python run_all.py
```

Browser terbuka otomatis ke `http://localhost:5000`.
Tekan **Ctrl+C** untuk mematikan semua node.

### Mode manual — untuk demo failover (4 terminal)

```bash
# Terminal 1..3 (node cabang)
python -m branch.main --name A
python -m branch.main --name B
python -m branch.main --name C

# Terminal 4 (web gateway)
python -m gateway.main
```

### Mode multi-laptop — tiap cabang di laptop berbeda (satu WiFi/LAN)

1. Pastikan semua laptop terhubung ke **jaringan WiFi/LAN yang sama**.
2. Cek IP tiap laptop: `hostname -I` (Linux) atau `ipconfig` (Windows).
3. Salin `network.example.json` menjadi `network.json`, isi IP tiap laptop:

   ```json
   {
     "branches": {
       "A": {"host": "192.168.1.10", "port": 8001},
       "B": {"host": "192.168.1.11", "port": 8002},
       "C": {"host": "192.168.1.12", "port": 8003}
     },
     "gateway": {"host": "192.168.1.10", "port": 5000}
   }
   ```
4. Salin folder proyek ini (termasuk `network.json` **yang sama**) ke semua laptop.
5. Jalankan node sesuai peran tiap laptop:

   ```bash
   # Laptop 1 — Cabang A + gateway (2 terminal)
   python -m branch.main --name A
   python -m gateway.main

   # Laptop 2 — Cabang B
   python -m branch.main --name B

   # Laptop 3 — Cabang C
   python -m branch.main --name C
   ```
6. Semua laptop membuka dashboard di `http://<IP-laptop-gateway>:5000`
   (contoh: `http://192.168.1.10:5000`).

> Catatan:
>
> - Keberadaan file `network.json` otomatis mengaktifkan mode jaringan
>   (server menerima koneksi dari komputer lain). Hapus/rename file itu
>   untuk kembali ke mode lokal.
> - Jika koneksi antar laptop gagal, izinkan port di firewall:
>   `sudo ufw allow 8001:8003/tcp && sudo ufw allow 5000/tcp` (Ubuntu),
>   atau klik "Allow" saat Windows Firewall bertanya.
> - `run_all.py` sengaja tidak bisa dipakai di mode ini (hanya untuk mode
>   satu komputer).
> - Gateway boleh diletakkan di laptop mana pun — samakan `gateway.host`
>   di `network.json`.

## Skenario Demo

1. **Replikasi** — Setor uang dan pilih "proses melalui Cabang A".
   Perhatikan terminal: Cabang A memproses lalu mengirim replikasi ke B dan C.
   Data di dashboard konsisten dari cabang mana pun.
2. **Failover** — Matikan Cabang B (Ctrl+C di terminalnya, atau jika memakai
   `run_all.py` jalankan `fuser -k 8002/tcp` dari terminal lain; port: A=8001,
   B=8002, C=8003). Dashboard menandai Cabang B **MATI**. Lakukan transaksi
   "melalui Cabang B" — permintaan otomatis dialihkan ke cabang lain dan
   tetap berhasil.
3. **Sinkronisasi ulang** — Lakukan beberapa transaksi selagi Cabang B mati,
   lalu hidupkan kembali Cabang B (`python -m branch.main --name B`). Saat
   startup, B menarik data terbaru dari peer (lihat log "Sinkronisasi startup
   dari peer berhasil").

## Struktur Kode (per modul)

```
bank-terdistribusi/
├── run_all.py             # launcher satu perintah
├── requirements.txt       # dependensi Python (Flask)
├── network.example.json   # contoh konfigurasi mode multi-laptop
├── common/
│   └── config.py          # konfigurasi terpusat (cabang, port, network.json, batas saldo)
├── branch/                # ── MODUL NODE CABANG ──
│   ├── main.py            # entry point (argparse + wiring)
│   ├── storage.py         # persistensi JSON + seed rekening
│   ├── bank.py            # logika bisnis: saldo, setor, tarik, transfer
│   ├── replication.py     # broadcast ke peer + sinkronisasi startup
│   └── server.py          # server XML-RPC multi-thread (register fungsi remote)
├── gateway/               # ── MODUL WEB GATEWAY ──
│   ├── main.py            # entry point Flask
│   ├── rpc_client.py      # klien RPC + failover + cek status
│   ├── routes.py          # route web (dashboard & transaksi)
│   ├── templates/         # halaman HTML (bahasa Indonesia)
│   └── static/            # style.css
└── data/                  # file JSON per cabang (dibuat otomatis)
```

### Batasan & validasi

- Jumlah transaksi harus **bilangan bulat positif** (validasi di node cabang).
- Saldo maksimum per rekening **Rp2.000.000.000** — aman dari batas integer
  XML-RPC (2³¹ − 1).
- Riwayat transaksi menyimpan **50 entri terakhir** per cabang.

## Reset Data

Hapus folder `data/` lalu jalankan ulang — rekening contoh dibuat kembali
otomatis (Andi Akbar Arya Putra, Muh. As'ad Habib, Muhammad Pasyafatir).
