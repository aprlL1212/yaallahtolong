"""Uji mesin analisis terhadap solusi teoritis (jalankan: python -m pytest -q)."""
import os, sys
import numpy as np, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from structura import engine as eg, examples, validation, report

E, B, H = 200000.0, 200.0, 300.0           # MPa, mm, mm  -> EI = 90.000 kN·m²
EI = E * 1e3 * B / 1e3 * (H / 1e3) ** 3 / 12


def beam(nodes, sup, nl=(), ml=(), n_el=None):
    n_el = n_el or len(nodes) - 1
    m = examples._m([(i + 1, x, y) for i, (x, y) in enumerate(nodes)],
                    [(i + 1, i + 1, i + 2, E, B, H) for i in range(n_el)], sup, nl, ml)
    return m


def run(m): return eg.analyze(m)
def u_of(res, n): k = res["ids"].index(n); return res["u"][3*k:3*k+3]


def test_cantilever_tip_load():
    P, L = 10.0, 3.0
    r = run(beam([(0, 0), (L, 0)], [(1, 1, 1, 1)], nl=[(2, 0, -P, 0)]))
    ux, uy, th = u_of(r, 2)
    assert uy == pytest.approx(-P * L**3 / (3 * EI), rel=1e-9)
    assert th == pytest.approx(-P * L**2 / (2 * EI), rel=1e-9)
    assert r["reactions"][1] == pytest.approx([0, P, P * L], rel=1e-9)


def test_simply_supported_udl():
    w, L = 10.0, 6.0
    r = run(beam([(0, 0), (3, 0), (6, 0)], [(1, 1, 1, 0), (3, 0, 1, 0)],
                 ml=[(1, "UDL", "Gravitasi", w, 0), (2, "UDL", "Gravitasi", w, 0)]))
    assert u_of(r, 2)[1] == pytest.approx(-5 * w * L**4 / (384 * EI), rel=1e-9)
    assert r["reactions"][1][1] == pytest.approx(w * L / 2) and r["reactions"][3][1] == pytest.approx(w * L / 2)
    xs = eg.sample_x(r["members"][1]); M = eg.internal(r["members"][1], xs)[2]
    assert M.max() == pytest.approx(w * L**2 / 8, rel=1e-9)         # momen maks di tengah bentang
    assert eg.internal(r["members"][1], [0])[1][0] == pytest.approx(w * L / 2)


def test_fixed_fixed_udl_and_point_load():
    w, L = 12.0, 6.0
    r = run(beam([(0, 0), (L, 0)], [(1, 1, 1, 1), (2, 1, 1, 1)], ml=[(1, "UDL", "Gravitasi", w, 0)]))
    M = eg.internal(r["members"][1], [0, L / 2, L])[2]
    assert M == pytest.approx([-w*L**2/12, w*L**2/24, -w*L**2/12], rel=1e-9)
    P, a = 30.0, 2.0; b = L - a
    r = run(beam([(0, 0), (L, 0)], [(1, 1, 1, 1), (2, 1, 1, 1)], ml=[(1, "Titik", "Gravitasi", P, a)]))
    assert r["reactions"][1][2] == pytest.approx(P * a * b**2 / L**2, rel=1e-9)   # momen jepit kiri = Pab²/L²
    assert r["reactions"][2][2] == pytest.approx(-P * a**2 * b / L**2, rel=1e-9)


def test_point_load_simply_supported_shear_jump():
    P, a, L = 20.0, 2.0, 6.0
    r = run(beam([(0, 0), (L, 0)], [(1, 1, 1, 0), (2, 0, 1, 0)], ml=[(1, "Titik", "Gravitasi", P, a)]))
    V = eg.internal(r["members"][1], [a - 1e-6, a + 1e-6])[1]
    assert V == pytest.approx([P * (L - a) / L, -P * a / L], abs=1e-4)


def test_portal_rigid_beam_sway():
    """Balok sangat kaku, tumpuan jepit: V kolom = H/2, momen dasar = H·h/4."""
    Hf, h = 20.0, 4.0
    m = examples._m([(1, 0, 0), (2, 0, h), (3, 6, h), (4, 6, 0)],
                    [(1, 1, 2, E, 200, 300), (2, 2, 3, E, 2000, 3000), (3, 3, 4, E, 200, 300)],
                    [(1, 1, 1, 1), (4, 1, 1, 1)], nl=[(2, Hf, 0, 0)])
    r = run(m)
    assert r["reactions"][1][0] == pytest.approx(-Hf / 2, rel=1e-3) and r["reactions"][4][0] == pytest.approx(-Hf / 2, rel=1e-3)
    assert abs(r["reactions"][1][2]) == pytest.approx(Hf * h / 4, rel=1e-3)


@pytest.mark.parametrize("name", list(examples.MODELS))
def test_equilibrium_examples(name):
    r = run(examples.MODELS[name]); eq = r["equilibrium"]
    assert max(abs(v) for v in eq.values()) < 1e-8 and r["residual"] < 1e-8


def test_inclined_member_gravity_equilibrium():
    m = examples._m([(1, 0, 0), (2, 3, 4), (3, 7, 4)], [(1, 1, 2, E, 300, 300), (2, 2, 3, E, 300, 300)],
                    [(1, 1, 1, 0), (3, 0, 1, 0)], nl=[(2, 5, 0, 2)],
                    ml=[(1, "UDL", "Gravitasi", 8, 0), (2, "Titik", "Lokal-y", 15, 1.5)])
    eq = run(m)["equilibrium"]; assert max(abs(v) for v in eq.values()) < 1e-8


def test_unstable_model_detected():
    m = beam([(0, 0), (4, 0)], [(1, 0, 1, 0), (2, 0, 1, 0)])           # 2 reaksi vertikal saja
    errs, _ = validation.validate(m); assert any("minimal 3" in e for e in errs)
    m = beam([(0, 0), (4, 0), (8, 0)], [(1, 0, 1, 0), (2, 0, 1, 0), (3, 0, 1, 0)], nl=[(3, 5, 0, 0)])
    assert not validation.validate(m)[0]                                 # lolos validasi (3 reaksi)...
    with pytest.raises(eg.ModelError): run(m)                            # ...tapi mekanisme horizontal


def test_validation_errors():
    m = beam([(0, 0), (4, 0), (9, 9)], [(1, 1, 1, 1)], ml=[(1, "Titik", "Gravitasi", 5, 10)], n_el=1)
    errs, _ = validation.validate(m)
    assert any("tidak terhubung" in e for e in errs) and any("0 < a < L" in e for e in errs)


def test_pdf_and_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("STRUCTURA_DB", str(tmp_path / "t.db"))
    from structura import storage
    m = examples.MODELS["Portal 2D (beton, beban lateral + merata)"]
    storage.save_project("p1", m); assert storage.load_project("p1") == m and storage.list_projects()[0][0] == "p1"
    pdf = report.build_pdf("p1", m, run(m)); assert pdf[:4] == b"%PDF" and len(pdf) > 5000
