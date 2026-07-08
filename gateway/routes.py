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
        try:
            history, _ = rpc_client.call_branch(sumber, "get_history")
        except rpc_client.SemuaCabangMati:
            pass  # cabang mati tepat setelah accounts terambil

    # Versi state tiap node — bukti replikasi: node sehat memiliki versi sama
    versions = {}
    for bid, hidup in status.items():
        if hidup:
            try:
                versions[bid] = rpc_client.call_direct(bid, "get_version")
            except rpc_client.RPC_ERRORS:
                versions[bid] = None
        else:
            versions[bid] = None

    return render_template(
        "index.html",
        status=status, accounts=accounts, history=history,
        sumber=sumber, branches=config.BRANCHES, versions=versions,
    )


@bp.route("/transaksi/<jenis>", methods=["GET", "POST"])
def transaksi(jenis):
    """Form + proses transaksi: setor, tarik, atau transfer."""
    if jenis not in JUDUL:
        abort(404)

    if request.method == "POST":
        cabang = request.form.get("cabang", "A")
        if cabang not in config.BRANCHES:
            flash("Cabang tidak dikenal.", "error")
            return redirect(url_for("web.transaksi", jenis=jenis))

        try:
            jumlah = int(request.form["jumlah"])
        except (KeyError, ValueError):
            flash("Jumlah harus berupa angka bulat.", "error")
            return redirect(url_for("web.transaksi", jenis=jenis))
        # Batasi di gateway: nilai di atas MAX_SALDO melebihi batas integer
        # XML-RPC (2^31-1) dan akan gagal dikirim ke node cabang.
        if jumlah < 1 or jumlah > config.MAX_SALDO:
            flash(f"Jumlah harus antara Rp 1 dan {rupiah(config.MAX_SALDO)}.", "error")
            return redirect(url_for("web.transaksi", jenis=jenis))

        try:
            if jenis == "transfer":
                hasil, dilayani = rpc_client.call_branch(
                    cabang, "transfer",
                    request.form.get("dari", ""), request.form.get("ke", ""), jumlah)
            else:
                method = "deposit" if jenis == "setor" else "withdraw"
                hasil, dilayani = rpc_client.call_branch(
                    cabang, method, request.form.get("rekening", ""), jumlah)
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
    status = rpc_client.branches_status()
    return render_template(
        "transaksi.html",
        jenis=jenis, judul=JUDUL[jenis],
        accounts=accounts, branches=config.BRANCHES, status=status,
        max_saldo=config.MAX_SALDO,
    )
