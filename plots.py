"""Visualisasi Plotly + data geometri diagram (dipakai juga oleh laporan PDF)."""
import numpy as np
import plotly.graph_objects as go
from . import engine as eg

COL = {"N": "#2f9e44", "V": "#e8590c", "M": "#1971c2"}
UNIT = {"N": "kN", "V": "kN", "M": "kN·m"}
NAME = {"N": "Gaya Aksial (N)", "V": "Gaya Geser (V)", "M": "Momen Lentur (M)"}


def _nodes(model):
    return {int(n["id"]): (float(n["x"]), float(n["y"])) for n in model["nodes"]}


def _size(nodes):
    p = np.array(list(nodes.values())); return max(np.ptp(p[:, 0]), np.ptp(p[:, 1]), 1.0)


def _rgba(h, a):
    return f"rgba({int(h[1:3],16)},{int(h[3:5],16)},{int(h[5:7],16)},{a})"


def _layout(fig, title):
    fig.update_layout(title=title, height=520, margin=dict(l=10, r=10, t=50, b=10), showlegend=False,
                      xaxis=dict(title="x (m)", zeroline=False),
                      yaxis=dict(title="y (m)", scaleanchor="x", zeroline=False), hovermode="closest")
    return fig


def _arrow(fig, x, y, fx, fy, text, color="#e03131", px=42):
    n = np.hypot(fx, fy)
    if n < 1e-12: return
    fig.add_annotation(x=x, y=y, ax=-px * fx / n, ay=px * fy / n, xref="x", yref="y", axref="pixel",
                       ayref="pixel", showarrow=True, arrowhead=2, arrowwidth=2, arrowcolor=color,
                       text=text, font=dict(color=color, size=11))


def model_fig(model, title="Model struktur & beban"):
    nodes = _nodes(model); fig = go.Figure()
    for m in model["members"]:
        (x1, y1), (x2, y2) = nodes[m["ni"]], nodes[m["nj"]]
        fig.add_trace(go.Scatter(x=[x1, x2], y=[y1, y2], mode="lines", line=dict(color="#495057", width=5),
                                 hoverinfo="text", text=f"Elemen {m['id']} ({m['b']:g}×{m['h']:g} mm, E={m['E']:g} MPa)"))
        fig.add_annotation(x=(x1+x2)/2, y=(y1+y2)/2, text=f"<b>E{m['id']}</b>", showarrow=False,
                           font=dict(size=11, color="#1971c2"), yshift=-14)
    fig.add_trace(go.Scatter(x=[p[0] for p in nodes.values()], y=[p[1] for p in nodes.values()],
                             mode="markers+text", text=[f"N{i}" for i in nodes], textposition="top right",
                             marker=dict(size=8, color="#1c7ed6"), hoverinfo="text"))
    sym = {(1, 1, 1): "square", (1, 1, 0): "triangle-up", (0, 1, 0): "circle-open", (1, 0, 0): "triangle-left"}
    sps = [s for s in model["supports"] if s["node"] in nodes]
    if sps:
        fig.add_trace(go.Scatter(
            x=[nodes[s["node"]][0] for s in sps], y=[nodes[s["node"]][1] for s in sps], mode="markers",
            marker=dict(size=17, color="#2b8a3e", symbol=[sym.get((int(s["ux"]), int(s["uy"]), int(s["rz"])), "diamond") for s in sps],
                        line=dict(width=2, color="#2b8a3e")),
            hoverinfo="text", text=[f"Tumpuan N{s['node']}: ux={int(s['ux'])}, uy={int(s['uy'])}, rz={int(s['rz'])}" for s in sps]))
    for nl in model["nodal_loads"]:
        x, y = nodes[nl["node"]]
        _arrow(fig, x, y, nl["Fx"], nl["Fy"], f"{np.hypot(nl['Fx'], nl['Fy']):g} kN")
        if nl["M"]:
            fig.add_annotation(x=x, y=y, text=f"M={nl['M']:g} kN·m {'↺' if nl['M'] > 0 else '↻'}", showarrow=False,
                               yshift=26, font=dict(color="#e03131", size=11))
    mem = {m["id"]: m for m in model["members"]}
    for ml in model["member_loads"]:
        m = mem[ml["member"]]; (x1, y1), (x2, y2) = nodes[m["ni"]], nodes[m["nj"]]
        L, c, s = eg.geom((x1, y1), (x2, y2)); gx, gy = eg.load_global(ml, c, s)
        if ml["type"] == "UDL":
            for t in np.linspace(0.1, 0.9, 5):
                _arrow(fig, x1 + t*(x2-x1), y1 + t*(y2-y1), gx, gy, f"{ml['value']:g} kN/m" if abs(t-0.5) < 1e-9 else "", "#f08c00", 30)
        else:
            _arrow(fig, x1 + c*ml["a"], y1 + s*ml["a"], gx, gy, f"{ml['value']:g} kN", "#f08c00")
    return _layout(fig, title)


def deformed_data(res, factor=1.0, n=21):
    nodes = res["nodes"]; u = res["u"]
    dmax = max(np.abs(u[0::3]).max(), np.abs(u[1::3]).max())
    sc = (0.1 * _size(nodes) / dmax if dmax > 0 else 1.0) * factor
    curves = []
    for mem in res["members"].values():
        x = np.linspace(0, mem["L"], n); ul, vl = eg.local_disp(mem, x); c, s = mem["c"], mem["s"]
        x0, y0 = nodes[mem["ni"]]
        curves.append((x0 + c*x + sc*(ul*c - vl*s), y0 + s*x + sc*(ul*s + vl*c)))
    return sc, curves


def deformed_fig(res, factor=1.0):
    sc, curves = deformed_data(res, factor); fig = go.Figure(); nodes = res["nodes"]
    for m in res["model"]["members"]:
        (x1, y1), (x2, y2) = nodes[m["ni"]], nodes[m["nj"]]
        fig.add_trace(go.Scatter(x=[x1, x2], y=[y1, y2], mode="lines", line=dict(color="#adb5bd", width=3, dash="dash"), hoverinfo="skip"))
    for X, Y in curves:
        fig.add_trace(go.Scatter(x=X, y=Y, mode="lines", line=dict(color="#e03131", width=4), hoverinfo="skip"))
    return _layout(fig, f"Bentuk deformasi (skala perbesaran ≈ {sc:,.0f}×)")


def diagram_data(res, kind, factor=1.0):
    nodes = res["nodes"]; raw = []
    for mem in res["members"].values():
        x = eg.sample_x(mem); N, V, M = eg.internal(mem, x); raw.append((mem, x, {"N": N, "V": V, "M": M}[kind]))
    vmax = max(np.abs(v).max() for _, _, v in raw) or 1.0
    sc = 0.15 * _size(nodes) / vmax * factor; sign = -1 if kind == "M" else 1   # M digambar di sisi tarik
    items = []
    for mem, x, v in raw:
        x0, y0 = nodes[mem["ni"]]; c, s = mem["c"], mem["s"]
        bx, by = x0 + c*x, y0 + s*x; off = sign * v * sc
        items.append(dict(id=mem["id"], x=x, val=v, bx=bx, by=by, ox=bx - s*off, oy=by + c*off))
    return sc, items


def diagram_fig(res, kind, factor=1.0):
    _, items = diagram_data(res, kind, factor); fig = go.Figure(); col = COL[kind]
    for it in items:
        fig.add_trace(go.Scatter(x=it["bx"], y=it["by"], mode="lines", line=dict(color="#495057", width=3), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=np.r_[it["bx"], it["ox"][::-1]], y=np.r_[it["by"], it["oy"][::-1]], mode="lines",
                                 fill="toself", fillcolor=_rgba(col, .25), line=dict(color=col, width=2), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=it["ox"], y=it["oy"], mode="markers", marker=dict(size=5, opacity=0), hoverinfo="text",
                                 text=[f"Elemen {it['id']}, x={a:.3f} m: {kind}={v:.3f} {UNIT[kind]}" for a, v in zip(it["x"], it["val"])]))
        v = it["val"]
        for i in {0, len(v) - 1, int(np.abs(v).argmax())}:
            if abs(v[i]) > 1e-6:
                fig.add_annotation(x=it["ox"][i], y=it["oy"][i], text=f"{v[i]:.2f}", showarrow=False, font=dict(color=col, size=11), yshift=10)
    note = " (digambar di sisi tarik)" if kind == "M" else ""
    return _layout(fig, f"{NAME[kind]} [{UNIT[kind]}]{note}")
