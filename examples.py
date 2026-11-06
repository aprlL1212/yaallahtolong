"""Contoh model & definisi tipe kolom tabel."""
import pandas as pd

COLS = {
    "nodes": {"id": "int64", "x": "float64", "y": "float64"},
    "members": {"id": "int64", "ni": "int64", "nj": "int64", "E": "float64", "b": "float64", "h": "float64"},
    "supports": {"node": "int64", "ux": "bool", "uy": "bool", "rz": "bool"},
    "nodal_loads": {"node": "int64", "Fx": "float64", "Fy": "float64", "M": "float64"},
    "member_loads": {"member": "int64", "type": "object", "dir": "object", "value": "float64", "a": "float64"},
}


def from_model(model):
    return {k: pd.DataFrame(model.get(k, []), columns=list(c)).astype(c) for k, c in COLS.items()}


def _m(nodes, members, supports, nl=(), ml=()):
    return dict(nodes=[dict(id=i, x=x, y=y) for i, x, y in nodes],
                members=[dict(id=i, ni=a, nj=b, E=E, b=bb, h=h) for i, a, b, E, bb, h in members],
                supports=[dict(node=n, ux=u, uy=v, rz=r) for n, u, v, r in supports],
                nodal_loads=[dict(node=n, Fx=a, Fy=b, M=m) for n, a, b, m in nl],
                member_loads=[dict(member=m, type=t, dir=d, value=v, a=a) for m, t, d, v, a in ml])


# Kategori & Model Lengkap Berbagai Gaya Soal Analisis Struktur
MODELS = {
    # --- Model Asli (Kompatibilitas Penuh) ---
    "Portal 2D (beton, beban lateral + merata)": _m(
        [(1, 0, 0), (2, 0, 4), (3, 6, 4), (4, 6, 0)],
        [(1, 1, 2, 25000, 400, 400), (2, 2, 3, 25000, 300, 500), (3, 3, 4, 25000, 400, 400)],
        [(1, True, True, True), (4, True, True, True)],
        nl=[(2, 20, 0, 0)], ml=[(2, "UDL", "Gravitasi", 15, 0)]),

    "Balok sederhana (baja, UDL 10 kN/m)": _m(
        [(1, 0, 0), (2, 3, 0), (3, 6, 0)],
        [(1, 1, 2, 200000, 200, 300), (2, 2, 3, 200000, 200, 300)],
        [(1, True, True, False), (3, False, True, False)],
        ml=[(1, "UDL", "Gravitasi", 10, 0), (2, "UDL", "Gravitasi", 10, 0)]),

    "Kantilever (beban titik ujung 10 kN)": _m(
        [(1, 0, 0), (2, 3, 0)], [(1, 1, 2, 200000, 200, 300)],
        [(1, True, True, True)], nl=[(2, 0, -10, 0)]),

    # --- Kategori 1: Portal Gedung Bertingkat & Industri ---
    "🏢 Portal 2 Lantai (Beban Gempa + Gravitasi)": _m(
        [(1, 0, 0), (2, 0, 3.5), (3, 0, 7.0), (4, 6, 7.0), (5, 6, 3.5), (6, 6, 0)],
        [(1, 1, 2, 25000, 400, 400), (2, 2, 3, 25000, 400, 400),
         (3, 3, 4, 25000, 300, 500), (4, 4, 5, 25000, 400, 400),
         (5, 5, 6, 25000, 400, 400), (6, 2, 5, 25000, 300, 500)],
        [(1, True, True, True), (6, True, True, True)],
        nl=[(2, 15, 0, 0), (3, 25, 0, 0)],
        ml=[(3, "UDL", "Gravitasi", 12, 0), (6, "UDL", "Gravitasi", 20, 0)]),

    "🏢 Portal 2 Bentang Multibay (Kolom Tengah)": _m(
        [(1, 0, 0), (2, 0, 4), (3, 5, 4), (4, 10, 4), (5, 10, 0), (6, 5, 0)],
        [(1, 1, 2, 25000, 400, 400), (2, 2, 3, 25000, 300, 500),
         (3, 3, 4, 25000, 300, 500), (4, 4, 5, 25000, 400, 400),
         (5, 6, 3, 25000, 400, 400)],
        [(1, True, True, True), (5, True, True, True), (6, True, True, True)],
        nl=[(2, 15, 0, 0)],
        ml=[(2, "UDL", "Gravitasi", 18, 0), (3, "UDL", "Gravitasi", 18, 0)]),

    "🏭 Portal Pelana Gudang (Gable Frame Rafter)": _m(
        [(1, 0, 0), (2, 0, 4), (3, 6, 5.5), (4, 12, 4), (5, 12, 0)],
        [(1, 1, 2, 200000, 200, 400), (2, 2, 3, 200000, 200, 350),
         (3, 3, 4, 200000, 200, 350), (4, 4, 5, 200000, 200, 400)],
        [(1, True, True, False), (5, True, True, False)],
        nl=[(2, 12, 0, 0)],
        ml=[(2, "UDL", "Gravitasi", 8, 0), (3, "UDL", "Gravitasi", 8, 0)]),

    "🏗️ Portal Baja Berpengaku Silang (X-Braced Frame)": _m(
        [(1, 0, 0), (2, 0, 4), (3, 6, 4), (4, 6, 0)],
        [(1, 1, 2, 200000, 250, 250), (2, 2, 3, 200000, 200, 350),
         (3, 4, 3, 200000, 250, 250),
         (4, 1, 3, 200000, 100, 100), (5, 4, 2, 200000, 100, 100)],
        [(1, True, True, False), (4, True, True, False)],
        nl=[(2, 40, 0, 0)]),

    # --- Kategori 2: Jembatan & Balok Menerus (Statis Tak Tentu) ---
    "🌉 Balok Menerus 2 Bentang (Statis Tak Tentu)": _m(
        [(1, 0, 0), (2, 6, 0), (3, 12, 0)],
        [(1, 1, 2, 200000, 250, 450), (2, 2, 3, 200000, 250, 450)],
        [(1, True, True, False), (2, False, True, False), (3, False, True, False)],
        ml=[(1, "UDL", "Gravitasi", 15, 0), (2, "UDL", "Gravitasi", 15, 0)]),

    "🌉 Balok Menerus 3 Bentang (Beban Kombinasi)": _m(
        [(1, 0, 0), (2, 5, 0), (3, 11, 0), (4, 16, 0)],
        [(1, 1, 2, 200000, 250, 450), (2, 2, 3, 200000, 250, 450), (3, 3, 4, 200000, 250, 450)],
        [(1, True, True, False), (2, False, True, False), (3, False, True, False), (4, False, True, False)],
        ml=[(1, "UDL", "Gravitasi", 12, 0),
            (2, "Titik", "Gravitasi", 35, 3.0),
            (3, "UDL", "Gravitasi", 12, 0)]),

    "🌉 Balok Kantilever Ganda (Overhang Kiri-Kanan)": _m(
        [(1, 0, 0), (2, 2, 0), (3, 8, 0), (4, 10, 0)],
        [(1, 1, 2, 200000, 200, 350), (2, 2, 3, 200000, 200, 350), (3, 3, 4, 200000, 200, 350)],
        [(2, True, True, False), (3, False, True, False)],
        nl=[(1, 0, -15, 0), (4, 0, -15, 0)],
        ml=[(2, "UDL", "Gravitasi", 20, 0)]),

    # --- Kategori 3: Kasus Khusus & Soal Ujian ---
    "📐 Balok dengan Beban Momen Terpusat (Loncatan M)": _m(
        [(1, 0, 0), (2, 4, 0), (3, 8, 0)],
        [(1, 1, 2, 200000, 200, 350), (2, 2, 3, 200000, 200, 350)],
        [(1, True, True, False), (3, False, True, False)],
        nl=[(2, 0, 0, 40)]),

    "📐 Balok Jepit-Sendi / Propped Cantilever": _m(
        [(1, 0, 0), (2, 6, 0)],
        [(1, 1, 2, 200000, 250, 400)],
        [(1, True, True, True), (2, False, True, False)],
        ml=[(1, "Titik", "Gravitasi", 30, 3.0)]),

    "📐 Struktur Tangga / Ramp Miring": _m(
        [(1, 0, 0), (2, 4, 3), (3, 6, 3)],
        [(1, 1, 2, 25000, 300, 350), (2, 2, 3, 25000, 300, 350)],
        [(1, True, True, False), (3, False, True, False)],
        ml=[(1, "UDL", "Gravitasi", 10, 0), (2, "UDL", "Gravitasi", 10, 0)]),
}


def load(name):
    return from_model(MODELS[name])
