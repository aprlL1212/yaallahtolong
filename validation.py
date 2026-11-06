"""Konversi tabel UI -> model dan validasi input."""
import numpy as np
import pandas as pd

SPEC = {
    "nodes": dict(num=["id", "x", "y"], req=["id", "x", "y"], ints=["id"]),
    "members": dict(num=["id", "ni", "nj", "E", "b", "h"], req=["id", "ni", "nj", "E", "b", "h"],
                    ints=["id", "ni", "nj"]),
    "supports": dict(num=["node"], req=["node"], ints=["node"], bool=["ux", "uy", "rz"]),
    "nodal_loads": dict(num=["node", "Fx", "Fy", "M"], req=["node"], ints=["node"], fill0=["Fx", "Fy", "M"]),
    "member_loads": dict(num=["member", "value", "a"], req=["member", "value"], ints=["member"],
                         fill0=["a"], txt={"type": "UDL", "dir": "Gravitasi"}),
}
LABEL = {"nodes": "Node", "members": "Elemen", "supports": "Tumpuan",
         "nodal_loads": "Beban titik buhul", "member_loads": "Beban elemen"}


def to_model(tables):
    errs, model = [], {}
    for key, sp in SPEC.items():
        df = tables[key].copy()
        for c in sp["num"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df[~df[sp["req"]].isna().all(axis=1)]
        for c in sp.get("fill0", []): df[c] = df[c].fillna(0.0)
        for c in sp.get("bool", []): df[c] = df[c].fillna(False).astype(bool)
        for c, d in sp.get("txt", {}).items(): df[c] = df[c].fillna(d).astype(str)
        bad = df[sp["req"]].isna().any(axis=1)
        if bad.any():
            errs.append(f"Tabel {LABEL[key]}: ada {int(bad.sum())} baris belum lengkap/bukan angka.")
        recs = df[~bad].to_dict("records")
        for r in recs:
            for c in sp["ints"]: r[c] = int(round(r[c]))
        model[key] = recs
    return model, errs


def validate(model):
    """Return (errors, warnings)."""
    E, W = [], []
    nodes, mems = model["nodes"], model["members"]
    if not nodes: E.append("Belum ada node.")
    if not mems: E.append("Belum ada elemen.")
    nid = [n["id"] for n in nodes]; mid = [m["id"] for m in mems]
    if len(set(nid)) != len(nid): E.append("ID node duplikat.")
    if len(set(mid)) != len(mid): E.append("ID elemen duplikat.")
    pts = {n["id"]: (n["x"], n["y"]) for n in nodes}
    ids = list(pts)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            if np.hypot(pts[ids[a]][0] - pts[ids[b]][0], pts[ids[a]][1] - pts[ids[b]][1]) < 1e-6:
                E.append(f"Node {ids[a]} dan {ids[b]} berada pada posisi yang sama.")
    L = {}; used = set(); pairs = set(); adj = {i: set() for i in ids}
    for m in mems:
        i, j = m["ni"], m["nj"]
        if i not in pts or j not in pts:
            E.append(f"Elemen {m['id']} merujuk node yang tidak ada ({i}-{j})."); continue
        if i == j: E.append(f"Elemen {m['id']}: node awal = node akhir."); continue
        L[m["id"]] = float(np.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]))
        if L[m["id"]] < 1e-6: E.append(f"Elemen {m['id']} panjangnya nol.")
        for k, nm in (("E", "Modulus E"), ("b", "Lebar b"), ("h", "Tinggi h")):
            if m[k] <= 0: E.append(f"Elemen {m['id']}: {nm} harus > 0.")
        used |= {i, j}; adj[i].add(j); adj[j].add(i)
        p = frozenset((i, j))
        if p in pairs: W.append(f"Ada lebih dari satu elemen di antara node {i}-{j}.")
        pairs.add(p)
    for n in set(ids) - used:
        E.append(f"Node {n} tidak terhubung ke elemen mana pun.")
    if ids and used:
        seen, stack = set(), [next(iter(used))]
        while stack:
            k = stack.pop()
            if k not in seen: seen.add(k); stack += list(adj[k] - seen)
        if used - seen: W.append("Struktur terdiri dari beberapa bagian terpisah; tiap bagian harus stabil sendiri.")
    nres, seen_s = 0, set()
    for sp in model["supports"]:
        if sp["node"] not in pts: E.append(f"Tumpuan merujuk node {sp['node']} yang tidak ada."); continue
        if sp["node"] in seen_s: E.append(f"Node {sp['node']} memiliki lebih dari satu baris tumpuan.")
        seen_s.add(sp["node"]); nres += int(sp["ux"]) + int(sp["uy"]) + int(sp["rz"])
    if nres < 3: E.append(f"Jumlah reaksi tumpuan = {nres}; minimal 3 agar struktur 2D stabil.")
    for nl in model["nodal_loads"]:
        if nl["node"] not in pts: E.append(f"Beban titik buhul merujuk node {nl['node']} yang tidak ada.")
    for ml in model["member_loads"]:
        if ml["member"] not in L: E.append(f"Beban elemen merujuk elemen {ml['member']} yang tidak valid."); continue
        if ml["type"] not in ("UDL", "Titik"): E.append("Jenis beban elemen harus UDL atau Titik.")
        if ml["dir"] not in ("Gravitasi", "Lokal-y", "Lokal-x"): E.append("Arah beban elemen tidak dikenal.")
        if ml["type"] == "Titik" and not (0 < ml["a"] < L[ml["member"]]):
            E.append(f"Beban titik pada elemen {ml['member']}: jarak a harus 0 < a < L ({L[ml['member']]:.3f} m).")
    if not model["nodal_loads"] and not model["member_loads"]:
        W.append("Tidak ada beban; hasil analisis akan bernilai nol.")
    return E, W
