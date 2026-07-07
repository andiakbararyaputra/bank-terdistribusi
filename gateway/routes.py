"""Route web gateway (Flask blueprint) — antarmuka pengguna sistem bank."""
from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)

from common import config
from gateway import rpc_client

bp = Blueprint("web", __name__)

JUDUL = {
    "setor": "Setor Tunai",
    "tarik": "Tarik Tunai",
    "transfer": "Transfer Antar Rekening",
}


@bp.app_template_filter("rupiah")
def rupiah(n):
    """Format angka menjadi 'Rp 1.000.000' di template."""
    return "Rp " + f"{int(n):,}".replace(",", ".")


def _ambil_accounts(cabang="A"):
    """Ambil daftar rekening dari cabang mana pun yang hidup."""
    try:
        return rpc_client.call_branch(cabang, "get_accounts")
    except rpc_client.SemuaCabangMati:
        return {}, None


@bp.route("/")
def index():
    """Dashboard: status node, daftar rekening, riwayat transaksi."""
    status = rpc_client.branches_status()
    accounts, sumber = _ambil_accounts()
    history = []
    if sumber:
        history, _ = rpc_client.call_branch(sumber, "get_history")
    return render_template(
        "index.html",
        status=status, accounts=accounts, history=history,
        sumber=sumber, branches=config.BRANCHES,
    )


@bp.route("/transaksi/<jenis>", methods=["GET", "POST"])
def transaksi(jenis):
    """Form + proses transaksi: setor, tarik, atau transfer."""
    if jenis not in JUDUL:
        abort(404)

    if request.method == "POST":
        cabang = request.form.get("cabang", "A")
        try:
            jumlah = int(request.form["jumlah"])
        except (KeyError, ValueError):
            flash("Jumlah harus berupa angka bulat.", "error")
            return redirect(url_for("web.transaksi", jenis=jenis))

        try:
            if jenis == "transfer":
                hasil, dilayani = rpc_client.call_branch(
                    cabang, "transfer",
                    request.form["dari"], request.form["ke"], jumlah)
            else:
                method = "deposit" if jenis == "setor" else "withdraw"
                hasil, dilayani = rpc_client.call_branch(
                    cabang, method, request.form["rekening"], jumlah)
        except rpc_client.SemuaCabangMati:
            flash("Semua cabang tidak dapat dihubungi — transaksi gagal.", "error")
            return redirect(url_for("web.index"))

        flash(hasil["pesan"], "sukses" if hasil.get("ok") else "error")
        if dilayani != cabang:
            flash(
                f"{config.branch_name(cabang)} tidak merespons — permintaan "
                f"otomatis dialihkan ke {config.branch_name(dilayani)} (failover).",
                "info")
        return redirect(url_for("web.index"))

    accounts, _ = _ambil_accounts()
    return render_template(
        "transaksi.html",
        jenis=jenis, judul=JUDUL[jenis],
        accounts=accounts, branches=config.BRANCHES,
    )
