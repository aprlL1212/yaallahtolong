"""Laporan PDF (ReportLab). Gambar dibuat langsung dengan reportlab.graphics."""
import datetime
import io
import numpy as np
import pandas as pd
from reportlab.graphics.shapes import Drawing, Polygon, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether
from . import engine as eg, plots

ASUMSI = ["Struktur portal 2D, material elastis linier, perpindahan kecil (orde pertama), beban statik.",
          "Elemen frame Euler-Bernoulli: 3 DOF per node (Ux, Uy, Rz); deformasi geser diabaikan.",
          "Penampang persegi: A = b·h, I = b·h³/12. Semua sambungan antar elemen kaku (tanpa sendi).",
          "Satuan: panjang m, gaya kN, momen kN·m, E dalam MPa, b dan h dalam mm.",
          "Konvensi: N tarik (+); V (+) bila gaya kiri-potongan ke atas pada sumbu lokal; M sagging (+).",
          "Aplikasi untuk pembelajaran; bukan pengganti analisis dan verifikasi insinyur profesional."]


def _f(v):
    if isinstance(v, (float, np.floating)): return "0" if abs(v) < 1e-9 else f"{v:.4g}"
    return str(v)


def _tbl(df):
    data = [list(df.columns)] + [[_f(v) for v in r] for r in df.itertuples(index=False)]
    t = Table(data, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c3d7a")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), .25, colors.grey),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f3f5")]),
                           ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return t


def _drawing(res, kind, W=500, H=250):
    model = res["model"]; nodes = res["nodes"]
    base = [(np.array([nodes[m["ni"]][0], nodes[m["nj"]][0]]), np.array([nodes[m["ni"]][1], nodes[m["nj"]][1]])) for m in model["members"]]
    layers, items = [(x, y, "base") for x, y in base], []
    if kind == "def":
        layers = [(x, y, "ghost") for x, y in base] + [(X, Y, "def") for X, Y in plots.deformed_data(res)[1]]
    elif kind in "NVM":
        items = plots.diagram_data(res, kind)[1]
        layers += [(np.r_[i["bx"], i["ox"][::-1]], np.r_[i["by"], i["oy"][::-1]], "diag") for i in items]
    xs = np.concatenate([l[0] for l in layers]); ys = np.concatenate([l[1] for l in layers])
    dx, dy = max(np.ptp(xs), 1e-9), max(np.ptp(ys), 1e-9); sc = min((W - 60) / dx, (H - 50) / dy)
    tr = lambda x, y: ((W - dx*sc)/2 + (np.asarray(x) - xs.min())*sc, (H - dy*sc)/2 + (np.asarray(y) - ys.min())*sc)
    d = Drawing(W, H)
    for x, y, st in layers:
        pts = np.column_stack(tr(x, y)).ravel().tolist()
        if st == "diag":
            d.add(Polygon(pts, fillColor=colors.Color(.1, .4, .8, .25), strokeColor=colors.HexColor(plots.COL[kind]), strokeWidth=1))
        else:
            d.add(PolyLine(pts, strokeColor={"base": colors.black, "ghost": colors.grey, "def": colors.red}[st],
                           strokeWidth=2 if st != "ghost" else 1, strokeDashArray=[3, 2] if st == "ghost" else None))
    for sp in model["supports"]:
        X, Y = tr(*nodes[sp["node"]]); d.add(Polygon([X, Y, X-5, Y-9, X+5, Y-9], fillColor=colors.green, strokeColor=colors.green))
    for it in items:
        v = it["val"]
        for i in {0, len(v)-1, int(np.abs(v).argmax())}:
            if abs(v[i]) > 1e-6:
                X, Y = tr(it["ox"][i], it["oy"][i]); d.add(String(float(X) + 2, float(Y) + 3, f"{v[i]:.2f}", fontSize=7))
    return d


def build_pdf(name, model, res):
    ss = getSampleStyleSheet(); H1, H2, B = ss["Title"], ss["Heading2"], ss["BodyText"]
    t = eg.tables(res); S = []
    S += [Paragraph("Structura — Laporan Analisis Struktur Portal 2D", H1),
          Paragraph(f"Proyek: <b>{name}</b> &nbsp;|&nbsp; Tanggal: {datetime.datetime.now():%d-%m-%Y %H:%M}", B), Spacer(1, 6),
          Paragraph("Metode: kekakuan matriks (direct stiffness), K·u = F, elastis linier statik.", B),
          Paragraph("Asumsi dan Catatan", H2)] + [Paragraph("• " + a, B) for a in ASUMSI]
    S.append(Paragraph("1. Data Input", H2))
    nd = pd.DataFrame(model["nodes"]).rename(columns={"id": "Node", "x": "x (m)", "y": "y (m)"})
    mm = []
    for m in model["members"]:
        E, A, I = eg.section(m)
        mm.append({"Elemen": m["id"], "Node i": m["ni"], "Node j": m["nj"], "E (MPa)": m["E"], "b (mm)": m["b"], "h (mm)": m["h"],
                   "A (cm²)": A*1e4, "I (cm⁴)": I*1e8})
    sp = pd.DataFrame([{"Node": s["node"], "Ux": "Tertahan" if s["ux"] else "-", "Uy": "Tertahan" if s["uy"] else "-",
                        "Rz": "Tertahan" if s["rz"] else "-"} for s in model["supports"]])
    nl = pd.DataFrame(model["nodal_loads"]).rename(columns={"node": "Node", "Fx": "Fx (kN)", "Fy": "Fy (kN)", "M": "M (kN·m)"})
    ml = pd.DataFrame([{"Elemen": m["member"], "Jenis": m["type"], "Arah": m["dir"],
                        "Nilai": f"{m['value']:g} " + ("kN/m" if m["type"] == "UDL" else "kN"),
                        "a (m)": m["a"] if m["type"] == "Titik" else "-"} for m in model["member_loads"]])
    for title, df in (("Node", nd), ("Elemen & penampang", pd.DataFrame(mm)), ("Tumpuan", sp), ("Beban titik buhul", nl), ("Beban elemen", ml)):
        if len(df): S += [Paragraph(f"<b>{title}</b>", B), _tbl(df), Spacer(1, 6)]
    S.append(Paragraph("2. Hasil Analisis", H2))
    for title, df in (("Perpindahan titik buhul", t["disp"]), ("Reaksi tumpuan", t["reac"]),
                      ("Gaya dalam di ujung elemen", t["forces"]), ("Nilai ekstrem gaya dalam", t["ext"])):
        S += [Paragraph(f"<b>{title}</b>", B), _tbl(df), Spacer(1, 6)]
    eq = res["equilibrium"]
    S += [Paragraph("3. Verifikasi Keseimbangan (beban + reaksi, harus ≈ 0)", H2),
          Paragraph(f"ΣFx = {eq['SFx']:.2e} kN; ΣFy = {eq['SFy']:.2e} kN; ΣM(O) = {eq['SM']:.2e} kN·m; residu K·u−F = {res['residual']:.2e}", B),
          Paragraph("4. Gambar", H2)]
    for kind, title in (("model", "Model struktur"), ("def", "Bentuk deformasi (diperbesar)"), ("N", "Diagram gaya aksial N (kN)"),
                        ("V", "Diagram gaya geser V (kN)"), ("M", "Diagram momen lentur M (kN·m, sisi tarik)")):
        S.append(KeepTogether([Paragraph(f"<b>{title}</b>", B), _drawing(res, kind)]))
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm,
                      title=f"Structura - {name}").build(S, onFirstPage=_foot, onLaterPages=_foot)
    return buf.getvalue()


def _foot(c, doc):
    c.setFont("Helvetica", 7); c.drawString(2*cm, 1*cm, "Structura — alat bantu belajar; verifikasi oleh insinyur profesional diperlukan.")
    c.drawRightString(A4[0] - 2*cm, 1*cm, f"Hal. {doc.page}")
