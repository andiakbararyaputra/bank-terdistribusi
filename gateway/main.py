"""Entry point web gateway.

Cara menjalankan (dari folder bank-terdistribusi):
    python -m gateway.main
"""
import logging
import socket

from flask import Flask

from common import config
from gateway.routes import bp


def create_app():
    app = Flask(__name__)
    app.secret_key = "demo-sisdis-bank"  # hanya untuk flash message (bukan produksi)
    app.register_blueprint(bp)
    return app


def main():
    # Timeout pendek agar cek status cabang yang mati tidak menggantung
    socket.setdefaulttimeout(2)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    app = create_app()
    if config.LAN_MODE:
        print("[Gateway] Mode jaringan (LAN) aktif — network.json terdeteksi.",
              flush=True)
        print(f"[Gateway] Laptop lain dapat membuka: "
              f"http://{config.GATEWAY_HOST}:{config.GATEWAY_PORT}", flush=True)
    print(f"[Gateway] Web aktif di http://{config.GATEWAY_HOST}:{config.GATEWAY_PORT}",
          flush=True)
    app.run(host=config.BIND_HOST, port=config.GATEWAY_PORT, debug=False)


if __name__ == "__main__":
    main()
