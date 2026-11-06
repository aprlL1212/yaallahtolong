"""Uji modul beban bergerak (moving load) dan kompatibilitasnya dengan mesin analisis Structura."""
import os, sys
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from structura import moving_load, engine as eg


def test_moving_load_equilibrium_and_moments():
    L = 20.0
    P = 100.0
    x = 4.6

    # Cek nilai reaksi tumpuan pada x = 4.6 m, L = 20 m, P = 100 kN
    r1, r2 = moving_load.reactions(L, P, x)
    assert r1 == pytest.approx(77.0, abs=1e-2)
    assert r2 == pytest.approx(23.0, abs=1e-2)
    assert (r1 + r2) == pytest.approx(P, abs=1e-7)

    # Cek momen di bawah beban pada x = 4.6m
    m_curr = moving_load.moment_under_load(L, P, x)
    assert m_curr == pytest.approx(354.2, abs=1e-2)

    # Cek momen puncak di tengah bentang (x = L / 2) -> PL / 4 = 100 * 20 / 4 = 500 kNm
    m_mid = moving_load.moment_under_load(L, P, L / 2.0)
    assert m_mid == pytest.approx(500.0, abs=1e-5)


def test_internal_diagrams_shear_jump():
    L = 20.0
    P = 100.0
    x = 4.6

    z, V, M = moving_load.beam_diagrams(L, P, x, n_pts=201)

    # Sebelum beban x: V = R1 = 77.0
    # Sesudah beban x: V = -R2 = -23.0
    z_left = x - 0.05
    z_right = x + 0.05

    v_left = np.interp(z_left, z, V)
    v_right = np.interp(z_right, z, V)

    assert v_left == pytest.approx(77.0, abs=0.5)
    assert v_right == pytest.approx(-23.0, abs=0.5)

    # Momen di tumpuan z=0 dan z=L harus 0
    assert M[0] == pytest.approx(0.0, abs=1e-6)
    assert M[-1] == pytest.approx(0.0, abs=1e-6)


def test_matrix_solver_integration():
    """Memverifikasi bahwa model yang dihasilkan fungsi to_structura_model

    dapat diselesaikan oleh mesin kekakuan Structura dan memberikan hasil yang sama persis dengan teori.
    """
    L = 20.0
    P = 100.0
    x = 10.0  # Beban di tengah bentang

    model = moving_load.to_structura_model(L, P, x, num_elements=10)
    res = eg.analyze(model)

    # Cek keseimbangan global
    eq = res["equilibrium"]
    assert abs(eq["SFx"]) < 1e-6
    assert abs(eq["SFy"]) < 1e-6
    assert abs(eq["SM"]) < 1e-6

    # Reaksi pada node 1 dan node terakhir harus 50 kN
    r_node1 = res["reactions"][1][1]
    r_last = res["reactions"][len(model["nodes"])][1]
    assert r_node1 == pytest.approx(50.0, abs=1e-4)
    assert r_last == pytest.approx(50.0, abs=1e-4)

    # Momen maksimum pada elemen tengah mendekati 500 kNm
    tb = eg.tables(res)
    ext_m = tb["ext"]["M maks + (kN·m)"].max()
    assert ext_m == pytest.approx(500.0, rel=1e-2)


def test_html_render_output():
    html = moving_load.render_moving_load_html(L=20.0, P=100.0, initial_x=4.6)
    assert "A moving load. A growing graph." in html
    assert "R₁ + R₂ = P = 100 kN" in html
    assert "Bending moment as the truck moves" in html
    assert "simSvg" in html
    assert "mathCard" in html
