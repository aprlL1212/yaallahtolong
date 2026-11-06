"""Mesin analisis: metode kekakuan matriks, portal 2D, elastis linier statik.
Satuan: kN, m, kN/m^2 (E), rad. Konvensi gaya dalam: N tarik (+), V (+) bila
gaya kiri-potongan ke atas (sumbu lokal y), M sagging (+) = serat bawah tarik."""
import numpy as np
import pandas as pd
from scipy import linalg


class ModelError(Exception):
    """Model tidak dapat dianalisis (mis. struktur tidak stabil)."""


def geom(p1, p2):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = float(np.hypot(dx, dy))
    return L, dx / L, dy / L


def section(m):
    """E [MPa], b,h [mm] -> E [kN/m2], A [m2], I [m4] (penampang persegi)."""
    b, h = m["b"] / 1e3, m["h"] / 1e3
    return m["E"] * 1e3, b * h, b * h ** 3 / 12


def k_local(E, A, I, L):
    a, b = E * A / L, E * I / L ** 3
    return np.array([
        [a, 0, 0, -a, 0, 0],
        [0, 12*b, 6*b*L, 0, -12*b, 6*b*L],
        [0, 6*b*L, 4*b*L*L, 0, -6*b*L, 2*b*L*L],
        [-a, 0, 0, a, 0, 0],
        [0, -12*b, -6*b*L, 0, 12*b, -6*b*L],
        [0, 6*b*L, 2*b*L*L, 0, -6*b*L, 4*b*L*L]])


def rot6(c, s):
    R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1.0]])
    T = np.zeros((6, 6)); T[:3, :3] = R; T[3:, 3:] = R
    return T


def load_local(ml, c, s):
    """Komponen beban (px, py) pada sumbu lokal. Gravitasi = ke bawah (global -Y)."""
    v = float(ml["value"])
    if ml["dir"] == "Gravitasi":
        return -v * s, -v * c
    return (v, 0.0) if ml["dir"] == "Lokal-x" else (0.0, v)


def load_global(ml, c, s):
    px, py = load_local(ml, c, s)
    return px * c - py * s, px * s + py * c


def fixed_end(ml, L, c, s):
    """Gaya ujung jepit = reaksi tumpuan jepit pada batang (berlawanan arah beban), sumbu lokal."""
    px, py = load_local(ml, c, s)
    if ml["type"] == "UDL":
        return -np.array([px*L/2, py*L/2, py*L*L/12, px*L/2, py*L/2, -py*L*L/12])
    a = float(ml["a"]); b = L - a
    return -np.array([px*b/L, py*b*b*(3*a+b)/L**3, py*a*b*b/L**2,
                      px*a/L, py*a*a*(a+3*b)/L**3, -py*a*a*b/L**2])


def analyze(model):
    nodes = {int(n["id"]): (float(n["x"]), float(n["y"])) for n in model["nodes"]}
    ids = list(nodes); idx = {i: k for k, i in enumerate(ids)}; nd = 3 * len(ids)
    K = np.zeros((nd, nd)); F = np.zeros(nd); mems = {}
    for nl in model["nodal_loads"]:
        k = idx[int(nl["node"])]
        F[3*k:3*k+3] += [nl["Fx"], nl["Fy"], nl["M"]]
    for m in model["members"]:
        i, j = int(m["ni"]), int(m["nj"])
        L, c, s = geom(nodes[i], nodes[j]); E, A, I = section(m)
        T = rot6(c, s); kl = k_local(E, A, I, L)
        dofs = np.r_[3*idx[i]:3*idx[i]+3, 3*idx[j]:3*idx[j]+3]
        K[np.ix_(dofs, dofs)] += T.T @ kl @ T
        mls = [ml for ml in model["member_loads"] if int(ml["member"]) == int(m["id"])]
        fe = sum((fixed_end(ml, L, c, s) for ml in mls), np.zeros(6))
        F[dofs] -= T.T @ fe                      # beban ekivalen titik buhul
        mems[int(m["id"])] = dict(id=int(m["id"]), ni=i, nj=j, L=L, c=c, s=s, T=T,
                                  kl=kl, dofs=dofs, fe=fe, loads=mls, E=E, A=A, I=I)
    fixed = sorted({3*idx[int(sp["node"])] + q for sp in model["supports"]
                    for q, key in enumerate(("ux", "uy", "rz")) if sp[key]})
    free = [d for d in range(nd) if d not in fixed]
    u = np.zeros(nd)
    if free:
        Kff = K[np.ix_(free, free)]
        dg = np.sqrt(np.diag(Kff)); lam = linalg.eigvalsh(Kff / np.outer(dg, dg))
        if lam[0] <= 1e-10 * lam[-1]:
            raise ModelError("Struktur tidak stabil (mekanisme/tumpuan kurang atau salah "
                             "arah). Periksa tumpuan dan konektivitas elemen.")
        u[free] = linalg.solve(Kff, F[free], assume_a="pos")
    Rfull = np.zeros(nd); Rfull[fixed] = (K @ u - F)[fixed]
    for mem in mems.values():
        mem["ul"] = mem["T"] @ u[mem["dofs"]]
        mem["f"] = mem["kl"] @ mem["ul"] + mem["fe"]   # gaya ujung elemen (lokal)
    res = dict(model=model, ids=ids, nodes=nodes, u=u, members=mems,
               reactions={ids[d // 3]: Rfull[3*(d//3):3*(d//3)+3] for d in fixed},
               residual=float(np.abs((K @ u - F)[free]).max()) if free else 0.0)
    res["equilibrium"] = _equilibrium(res)
    return res


def _equilibrium(res):
    """Jumlah beban + reaksi (harus 0): SFx, SFy, SM terhadap titik asal."""
    Sx = Sy = Sm = 0.0
    def add(fx, fy, m, x, y):
        nonlocal Sx, Sy, Sm
        Sx += fx; Sy += fy; Sm += m + x * fy - y * fx
    for nl in res["model"]["nodal_loads"]:
        x, y = res["nodes"][int(nl["node"])]; add(nl["Fx"], nl["Fy"], nl["M"], x, y)
    for mem in res["members"].values():
        x0, y0 = res["nodes"][mem["ni"]]; L, c, s = mem["L"], mem["c"], mem["s"]
        for ml in mem["loads"]:
            gx, gy = load_global(ml, c, s)
            if ml["type"] == "UDL":
                add(gx*L, gy*L, 0, x0 + c*L/2, y0 + s*L/2)
            else:
                a = float(ml["a"]); add(gx, gy, 0, x0 + c*a, y0 + s*a)
    for n, r in res["reactions"].items():
        x, y = res["nodes"][n]; add(r[0], r[1], r[2], x, y)
    return dict(SFx=Sx, SFy=Sy, SM=Sm)


def sample_x(mem, n=41):
    L = mem["L"]; xs = list(np.linspace(0, L, n))
    for ml in mem["loads"]:
        if ml["type"] != "UDL":
            a = float(ml["a"]); xs += [max(a - 1e-9 * L, 0), a, min(a + 1e-9 * L, L)]
    return np.unique(np.clip(xs, 0, L))


def internal(mem, x):
    """N(x), V(x), M(x) sepanjang elemen dari keseimbangan potongan kiri."""
    x = np.atleast_1d(np.asarray(x, float)); f = mem["f"]
    N = -f[0] * np.ones_like(x); V = f[1] * np.ones_like(x)
    M = -f[2] + f[1] * x
    for ml in mem["loads"]:
        px, py = load_local(ml, mem["c"], mem["s"])
        if ml["type"] == "UDL":
            N = N - px * x; V = V + py * x; M = M + py * x ** 2 / 2
        else:
            a = float(ml["a"]); on = (x > a).astype(float)
            N = N - px * on; V = V + py * on; M = M + py * (x - a) * on
    return N, V, M


def local_disp(mem, x):
    """Perpindahan lokal (u,v) sepanjang elemen: interpolasi linier/Hermite kubik."""
    u1, v1, t1, u2, v2, t2 = mem["ul"]; L = mem["L"]; r = np.asarray(x) / L
    u = u1 + (u2 - u1) * r
    v = (v1*(1-3*r**2+2*r**3) + t1*L*(r-2*r**2+r**3) + v2*(3*r**2-2*r**3) + t2*L*(r**3-r**2))
    return u, v


def tables(res):
    ids, u = res["ids"], res["u"]
    disp = pd.DataFrame([{"Node": n, "Ux (mm)": u[3*k]*1e3, "Uy (mm)": u[3*k+1]*1e3,
                          "Rz (rad)": u[3*k+2]} for k, n in enumerate(ids)])
    reac = pd.DataFrame([{"Node": n, "Rx (kN)": r[0], "Ry (kN)": r[1], "Mz (kN·m)": r[2]}
                         for n, r in res["reactions"].items()])
    rows, ext = [], []
    for mem in res["members"].values():
        e = internal(mem, [0, mem["L"]]); xs = sample_x(mem); N, V, M = internal(mem, xs)
        rows.append({"Elemen": mem["id"], "L (m)": mem["L"], "N awal (kN)": e[0][0], "V awal (kN)": e[1][0],
                     "M awal (kN·m)": e[2][0], "N akhir (kN)": e[0][1], "V akhir (kN)": e[1][1],
                     "M akhir (kN·m)": e[2][1]})
        ext.append({"Elemen": mem["id"], "|N| maks (kN)": abs(N).max(), "|V| maks (kN)": abs(V).max(),
                    "M maks + (kN·m)": M.max(), "M maks − (kN·m)": M.min(),
                    "x di |M| maks (m)": xs[np.abs(M).argmax()]})
    return dict(disp=disp, reac=reac, forces=pd.DataFrame(rows), ext=pd.DataFrame(ext))
