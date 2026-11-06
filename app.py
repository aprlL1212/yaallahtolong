"""Structura - antarmuka Streamlit. Jalankan: streamlit run app.py"""
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from structura import engine, examples, moving_load, plots, report, storage, validation

st.set_page_config(page_title="Structura", page_icon="🏗️", layout="wide")
st.markdown("""<style>
.hero{background:linear-gradient(120deg,#1c3d7a,#1971c2 60%,#22b8cf);color:#fff;padding:1.5rem 1.8rem;border-radius:16px;margin-bottom:1rem}
.hero h1{margin:0;color:#fff;font-size:2rem}.hero p{margin:.3rem 0 0;opacity:.92}
.card{border:1px solid rgba(128,128,128,.28);border-radius:14px;padding:1rem 1.1rem;height:100%}
div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.28);border-radius:12px;padding:.6rem .9rem}
.block-container{padding-top:1.5rem}
</style>""", unsafe_allow_html=True)

KEYS = list(examples.COLS)
ss = st.session_state
if "tables" not in ss:
    ss.tables = examples.load(next(iter(examples.MODELS))); ss.base = {k: v.copy() for k, v in ss.tables.items()}
    ss.name, ss.ver, ss.res, ss.sig, ss.pdf, ss.last = "Proyek baru", 0, None, None, None, None


def set_tables(tables, name):
    ss.tables, ss.name, ss.res, ss.pdf = tables, name, None, None
    ss.base = {k: v.copy() for k, v in tables.items()}; ss.ver += 1


def current_model():
    model, errs = validation.to_model(ss.tables)
    if not errs:
        e, w = validation.validate(model); errs += e
    else:
        w = []
    return model, errs, w


def show_msgs(errs, warns=()):
    for e in errs: st.error(e, icon="⛔")
    for w in warns: st.warning(w, icon="⚠️")


# 2 Menu Utama yang Jelas dan Terpisah
PAGES = ["🏗️ Perhitungan Portal 2D", "🚚 Simulasi Beban Bergerak"]

if "redirect_page" in ss:
    ss.nav_page = ss.pop("redirect_page")

if "nav_page" not in ss:
    ss.nav_page = PAGES[0]

page = st.sidebar.radio("Pilih Menu Utama", PAGES, key="nav_page")
st.sidebar.caption(f"Proyek aktif: **{ss.name}**")
st.sidebar.info("Alat bantu belajar Analisis Struktur. Bukan pengganti verifikasi profesional.")

# ==============================================================================
# MENU 1: PERHITUNGAN STRUKTUR PORTAL 2D (Metode Matriks)
# Menyatukan Dashboard, Input Model, Analisis & Hasil, Laporan PDF, dan Proyek
# ==============================================================================
if page.startswith("🏗️"):
    st.markdown('<div class="hero"><h1>🏗️ Structura — Analisis Portal 2D</h1><p>Perhitungan struktur portal & balok 2D dengan metode kekakuan matriks langsung (Direct Stiffness Method).</p></div>', unsafe_allow_html=True)
    
    tab_dash, tab_input, tab_analisis, tab_laporan, tab_proyek = st.tabs([
        "🏠 Dashboard & Mulai Cepat",
        "📐 Input Model",
        "🧮 Analisis & Hasil",
        "📄 Laporan PDF",
        "💾 Simpan / Buka Proyek"
    ])

    # ---------------- 1. Dashboard & Mulai Cepat ----------------
    with tab_dash:
        model, errs, warns = current_model()
        c = st.columns(5)
        c[0].metric("Node", len(model["nodes"])); c[1].metric("Elemen", len(model["members"]))
        c[2].metric("Tumpuan", len(model["supports"])); c[3].metric("Beban", len(model["nodal_loads"]) + len(model["member_loads"]))
        c[4].metric("Status analisis", "Selesai ✅" if ss.res else "Belum")
        st.write("")
        a, b = st.columns([1, 1])
        with a:
            st.markdown("#### Mulai Cepat & Contoh Soal")
            kat_pilihan = st.selectbox("Kategori Soal", ["Semua Kategori", "🏢 Portal Gedung & Industri", "🌉 Jembatan & Balok Menerus", "📐 Kasus Khusus & Ujian"])
            if kat_pilihan.startswith("🏢"):
                filtered_models = [k for k in examples.MODELS if any(s in k for s in ["🏢", "🏭", "🏗️", "Portal"])]
            elif kat_pilihan.startswith("🌉"):
                filtered_models = [k for k in examples.MODELS if any(s in k for s in ["🌉", "Menerus", "Overhang"])]
            elif kat_pilihan.startswith("📐"):
                filtered_models = [k for k in examples.MODELS if any(s in k for s in ["📐", "Momen", "Kantilever", "Tangga", "Propped"])]
            else:
                filtered_models = list(examples.MODELS)
            ex = st.selectbox("Pilih Model Soal", filtered_models)
            x, y = st.columns(2)
            if x.button("Muat contoh", width="stretch"): set_tables(examples.load(ex), ex); st.rerun()
            if y.button("Proyek kosong", width="stretch"): set_tables(examples.from_model({}), "Proyek baru"); st.rerun()
            st.markdown("**Alur kerja:** ① Input Model → ② Analisis & Hasil → ③ Simpan Proyek → ④ Ekspor PDF")
        with b:
            if not errs and model["members"]: st.plotly_chart(plots.model_fig(model, "Pratinjau model aktif"), width="stretch", key="chart_dash_preview")
            else: show_msgs(errs, warns)

        with st.expander("📘 Rumus & asumsi"):
            st.markdown(r"""
**Persamaan utama:** $\mathbf{K}\,\mathbf{u}=\mathbf{F}$, dengan $\mathbf{K}=\sum \mathbf{T}^T\mathbf{k}\,\mathbf{T}$. Reaksi: $\mathbf{R}=\mathbf{K}\mathbf{u}-\mathbf{F}$ pada DOF tertahan.
Beban elemen diubah menjadi beban ekivalen titik buhul $-\mathbf{T}^T\mathbf{f}_{e}$ (gaya ujung jepit). Gaya ujung elemen: $\mathbf{f}=\mathbf{k}\,\mathbf{T}\mathbf{u}_e+\mathbf{f}_e$.

**Matriks lokal frame** (EA/L, 12EI/L³, 6EI/L², 4EI/L, 2EI/L), $A=bh$, $I=bh^3/12$.
**Gaya dalam:** $N(x)=-(f_1+\int p_x)$, $V(x)=f_2+\int p_y$, $M(x)=-m_1+f_2x+\iint p_y$.
**Asumsi:** elastis linier, perpindahan kecil, Euler-Bernoulli, sambungan kaku, beban statik, penampang persegi.
**Konvensi:** N tarik (+); M sagging (+), diagram M digambar di sisi tarik.""")

    # ---------------- 2. Input Model ----------------
    with tab_input:
        st.subheader("📐 Input Geometri, Penampang & Pembebanan")
        L_col, R_col = st.columns([1.1, 1])
        cfg = st.column_config
        with L_col:
            ss.name = st.text_input("Nama proyek", ss.name, key="proj_name_input")
            t_sub = st.tabs(["Node", "Elemen & Penampang", "Tumpuan", "Beban"])
            ed = lambda k, **kw: st.data_editor(ss.base[k], key=f"ed_{k}_{ss.ver}", num_rows="dynamic", width="stretch", hide_index=True, **kw)
            with t_sub[0]:
                st.caption("Koordinat dalam meter (m).")
                ss.tables["nodes"] = ed("nodes", column_config={"id": cfg.NumberColumn("ID", step=1), "x": cfg.NumberColumn("x (m)", format="%.3f"), "y": cfg.NumberColumn("y (m)", format="%.3f")})
            with t_sub[1]:
                st.caption("Penampang persegi b × h. Beton ≈ 25.000 MPa, baja ≈ 200.000 MPa.")
                ss.tables["members"] = ed("members", column_config={"id": cfg.NumberColumn("ID", step=1), "ni": cfg.NumberColumn("Node i", step=1), "nj": cfg.NumberColumn("Node j", step=1),
                                          "E": cfg.NumberColumn("E (MPa)"), "b": cfg.NumberColumn("b (mm)"), "h": cfg.NumberColumn("h (mm)")})
            with t_sub[2]:
                st.caption("Centang DOF yang tertahan. Jepit = ux+uy+rz; sendi = ux+uy; rol = uy.")
                ss.tables["supports"] = ed("supports", column_config={"node": cfg.NumberColumn("Node", step=1), "ux": cfg.CheckboxColumn("Ux"), "uy": cfg.CheckboxColumn("Uy"), "rz": cfg.CheckboxColumn("Rz")})
            with t_sub[3]:
                st.markdown("**Beban titik buhul** (Fx, Fy +: ke kanan/atas; M +: berlawanan jarum jam)")
                ss.tables["nodal_loads"] = ed("nodal_loads", column_config={"node": cfg.NumberColumn("Node", step=1), "Fx": cfg.NumberColumn("Fx (kN)"), "Fy": cfg.NumberColumn("Fy (kN)"), "M": cfg.NumberColumn("M (kN·m)")})
                st.markdown("**Beban pada elemen** — Gravitasi: ke bawah; Lokal-y: ⟂ elemen; `a` = jarak dari node i (beban Titik)")
                ss.tables["member_loads"] = ed("member_loads", column_config={"member": cfg.NumberColumn("Elemen", step=1),
                                               "type": cfg.SelectboxColumn("Jenis", options=["UDL", "Titik"], default="UDL"),
                                               "dir": cfg.SelectboxColumn("Arah", options=["Gravitasi", "Lokal-y", "Lokal-x"], default="Gravitasi"),
                                               "value": cfg.NumberColumn("Nilai (kN/m | kN)"), "a": cfg.NumberColumn("a (m)")})
        with R_col:
            model, errs, warns = current_model()
            show_msgs(errs, warns)
            if model["members"] and not errs: st.plotly_chart(plots.model_fig(model), width="stretch", key="chart_input_preview")
            elif not errs: st.info("Tambahkan node dan elemen untuk melihat pratinjau.")

    # ---------------- 3. Analisis & Hasil ----------------
    with tab_analisis:
        st.subheader("🧮 Solusi Metode Kekakuan Langsung (K·u = F)")
        model, errs, warns = current_model(); show_msgs(errs, warns)
        if st.button("▶ Jalankan analisis", type="primary", disabled=bool(errs), key="btn_run_analysis"):
            try:
                ss.res = engine.analyze(model); ss.sig = json.dumps(model, sort_keys=True, default=float); ss.pdf = None
            except engine.ModelError as e:
                ss.res = None; st.error(str(e), icon="⛔")
        res = ss.res
        if res is not None and ss.sig != json.dumps(model, sort_keys=True, default=float):
            st.warning("Model berubah sejak analisis terakhir. Jalankan ulang analisis.", icon="⚠️")
        if res is not None:
            tb = engine.tables(res); u = res["u"]; ext = tb["ext"]
            c = st.columns(4)
            c[0].metric("|Ux| maks", f"{abs(u[0::3]).max()*1e3:.3f} mm"); c[1].metric("|Uy| maks", f"{abs(u[1::3]).max()*1e3:.3f} mm")
            c[2].metric("|V| maks", f"{ext['|V| maks (kN)'].max():.2f} kN"); c[3].metric("|M| maks", f"{max(ext['M maks + (kN·m)'].max(), -ext['M maks − (kN·m)'].min()):.2f} kN·m")
            sub_tabs = st.tabs(["Model & Beban", "Deformasi", "Aksial N", "Geser V", "Momen M", "Tabel", "Verifikasi"])
            with sub_tabs[0]: st.plotly_chart(plots.model_fig(res["model"]), width="stretch", key="chart_res_model")
            with sub_tabs[1]:
                f = st.slider("Faktor skala deformasi (relatif)", 0.1, 5.0, 1.0, 0.1, key="slider_def_f"); st.plotly_chart(plots.deformed_fig(res, f), width="stretch", key="chart_deformed")
            for t_diag, k in zip(sub_tabs[2:5], "NVM"):
                with t_diag: st.plotly_chart(plots.diagram_fig(res, k), width="stretch", key=f"chart_diag_{k}")
            with sub_tabs[5]:
                fmt = lambda df: {col: st.column_config.NumberColumn(col, format="%.6f" if "rad" in col else "%.4f") for col in df.columns if col not in ("Node", "Elemen")}
                for title, k in (("Perpindahan titik buhul", "disp"), ("Reaksi tumpuan", "reac"), ("Gaya dalam di ujung elemen (N, V, M)", "forces"), ("Nilai ekstrem per elemen", "ext")):
                    st.markdown(f"**{title}**"); st.dataframe(tb[k], hide_index=True, width="stretch", column_config=fmt(tb[k]))
                st.caption("Konvensi: N tarik (+) · V (+) bila gaya kiri-potongan ke atas (sumbu lokal) · M sagging (+).")
            with sub_tabs[6]:
                eq = res["equilibrium"]; ok = max(abs(eq["SFx"]), abs(eq["SFy"]), abs(eq["SM"])) < 1e-6
                st.markdown(f"**Keseimbangan global** (beban + reaksi):\n\n- ΣFx = `{eq['SFx']:.3e}` kN\n- ΣFy = `{eq['SFy']:.3e}` kN\n- ΣM (titik asal) = `{eq['SM']:.3e}` kN·m\n- Residu K·u − F (DOF bebas) = `{res['residual']:.3e}`")
                (st.success if ok else st.error)("Keseimbangan terpenuhi ✅" if ok else "Keseimbangan tidak terpenuhi — periksa model.")

    # ---------------- 4. Laporan PDF ----------------
    with tab_laporan:
        st.subheader("📄 Laporan Resmi Analisis Struktur")
        if ss.res is None:
            st.info("Jalankan analisis terlebih dahulu pada tab *Analisis & Hasil* sebelum membuat laporan.")
        else:
            if st.button("Buat laporan PDF", type="primary", key="btn_build_pdf"):
                ss.pdf = report.build_pdf(ss.name, ss.res["model"], ss.res)
            if ss.pdf:
                st.success("Laporan PDF berhasil dibuat dan siap diunduh!")
                st.download_button("⬇ Unduh Berkas PDF", ss.pdf, file_name=f"Structura_{ss.name.replace(' ', '_')}.pdf", mime="application/pdf", key="btn_download_pdf")

    # ---------------- 5. Simpan / Buka Proyek ----------------
    with tab_proyek:
        st.subheader("💾 Manajemen Penyimpanan Proyek")
        a_col, b_col = st.columns(2)
        with a_col:
            st.markdown("#### Simpan Proyek Aktif")
            p_name = st.text_input("Nama proyek simpan", ss.name, key="savename_tab")
            if st.button("Simpan ke Database", type="primary", disabled=not p_name.strip(), key="btn_save_proj"):
                model, errs = validation.to_model(ss.tables)
                storage.save_project(p_name.strip(), model); ss.name = p_name.strip(); st.success(f"Proyek '{p_name}' berhasil tersimpan.")
        with b_col:
            st.markdown("#### Buka / Hapus Proyek")
            rows = storage.list_projects()
            if not rows: st.info("Belum ada proyek tersimpan di database.")
            else:
                sel = st.selectbox("Pilih Proyek", [r[0] for r in rows], format_func=lambda n: f"{n}  ({dict(rows)[n]})", key="select_load_proj")
                x_b, y_b = st.columns(2)
                if x_b.button("Buka Proyek", width="stretch", key="btn_open_proj"):
                    set_tables(examples.from_model(storage.load_project(sel)), sel); st.success(f"Proyek '{sel}' dibuka."); st.rerun()
                if y_b.button("Hapus", width="stretch", key="btn_del_proj"):
                    storage.delete_project(sel); st.rerun()


# ==============================================================================
# MENU 2: SIMULASI BEBAN BERGERAK (INTERAKTIF DRAG & DROP, TANPA VIDEO)
# ==============================================================================
else:
    st.markdown('<div class="hero"><h1>🚚 Simulasi Beban Bergerak</h1><p>Visualisasi interaktif balok jembatan — seret mobil langsung dengan kursor/jari, amati reaksi dinamis R₁ & R₂, dan kurva momen bertumbuh real-time.</p></div>', unsafe_allow_html=True)
    
    # Preset & Parameter Controls
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.5, 1, 1, 1])
    preset = ctrl1.selectbox("Pilihan Skenario", [
        "🎯 Truk Standar (L=20m, P=100kN)",
        "🚛 Truk Standar Bina Marga BM-100 (L=25m, P=100kN)",
        "🚚 Truk AASHTO HS-20 (L=30m, P=145kN)",
        "🚗 Mobil Ringan (L=15m, P=25kN)",
        "⚙️ Kustom Sendiri"
    ])
    
    def_L, def_P, def_x = 20.0, 100.0, 4.6
    if "Bina Marga" in preset: def_L, def_P, def_x = 25.0, 100.0, 6.0
    elif "AASHTO" in preset: def_L, def_P, def_x = 30.0, 145.0, 8.0
    elif "Mobil" in preset: def_L, def_P, def_x = 15.0, 25.0, 3.5
    
    L_val = ctrl2.number_input("Bentang Jembatan L (m)", min_value=5.0, max_value=100.0, value=def_L, step=1.0)
    P_val = ctrl3.number_input("Beban Truk P (kN)", min_value=5.0, max_value=1000.0, value=def_P, step=5.0)
    x_val = ctrl4.slider("Posisi Awal x (m)", min_value=0.0, max_value=float(L_val), value=min(float(def_x), float(L_val)), step=0.1)

    # Render Component Beban Bergerak (Interaktif Drag & Drop, Bebas Teks Menumpuk)
    sim_html = moving_load.render_moving_load_html(L=L_val, P=P_val, initial_x=x_val)
    components.html(sim_html, height=580, scrolling=False)
    
    # Real-time Metrics
    r1, r2 = moving_load.reactions(L_val, P_val, x_val)
    m_curr = moving_load.moment_under_load(L_val, P_val, x_val)
    m_max_abs = (P_val * L_val) / 4.0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reaksi Kiri R₁", f"{r1:.2f} kN", delta=f"{r1/P_val*100:.1f}% P")
    c2.metric("Reaksi Kanan R₂", f"{r2:.2f} kN", delta=f"{r2/P_val*100:.1f}% P")
    c3.metric("Momen di Bawah Beban M(x)", f"{m_curr:.2f} kN·m")
    c4.metric("Momen Maks. Absolut (x=L/2)", f"{m_max_abs:.2f} kN·m", help="Terjadi tepat saat beban berada di tengah bentang (x = L / 2)")
    
    # Detail Tabs
    mv_tabs = st.tabs(["📊 Bidang Momen (BMD) & Geser (SFD)", "📈 Garis Pengaruh (Influence Line)", "🚀 Ekspor ke Solver Matriks Structura", "📘 Penjelasan Teori & Rumus"])
    
    with mv_tabs[0]:
        st.caption("Diagram gaya dalam seketika di sepanjang bentang balok untuk posisi truk saat ini.")
        col_bmd, col_sfd = st.columns(2)
        with col_bmd:
            st.plotly_chart(moving_load.plotly_diagrams_figure(L_val, P_val, x_val), width="stretch", key="chart_mv_bmd")
        with col_sfd:
            st.plotly_chart(moving_load.plotly_sfd_figure(L_val, P_val, x_val), width="stretch", key="chart_mv_sfd")
            
    with mv_tabs[1]:
        st.markdown("#### Garis Pengaruh (Influence Line)")
        st.caption("Garis pengaruh menunjukkan variasi nilai reaksi, gaya geser, atau momen pada titik potongan tertentu akibat pergerakan beban 1 kN di sepanjang jembatan.")
        sec_c = st.slider("Titik Potongan Tinjauan c (m)", 0.0, float(L_val), float(L_val)/2.0, 0.5)
        xs_il, il_r1, il_r2, il_vc, il_mc = moving_load.influence_lines(L_val, sec_c)
        
        il_fig = go.Figure()
        il_fig.add_trace(go.Scatter(x=xs_il, y=il_r1, mode="lines", name="GP Reaksi R₁", line=dict(color="#2563eb", width=2.5)))
        il_fig.add_trace(go.Scatter(x=xs_il, y=il_r2, mode="lines", name="GP Reaksi R₂", line=dict(color="#7c3aed", width=2.5)))
        il_fig.add_trace(go.Scatter(x=xs_il, y=il_mc, mode="lines", name=f"GP Momen di c={sec_c:.1f}m", line=dict(color="#1971c2", width=3, dash="dash")))
        il_fig.update_layout(title=f"Garis Pengaruh untuk Potongan c = {sec_c:.1f} m", xaxis_title="Posisi Beban Satuan x (m)", yaxis_title="Nilai Pengaruh", height=380, hovermode="x unified")
        st.plotly_chart(il_fig, width="stretch", key="chart_mv_il")
        
    with mv_tabs[2]:
        st.markdown("#### Integrasi dengan Mesin Analisis Matriks Structura")
        st.write("Anda dapat mengonversi jembatan beban bergerak ini menjadi model diskrit portal/balok 2D untuk dianalisis dengan metode kekakuan langsung ($K \\cdot u = F$).")
        n_elem = st.slider("Jumlah Elemen Diskrit", min_value=4, max_value=40, value=10, step=2)
        if st.button("🚀 Kirim ke Solver Matriks Structura", type="primary"):
            new_model = moving_load.to_structura_model(L=L_val, P=P_val, x=x_val, num_elements=n_elem)
            new_tables = examples.from_model(new_model)
            set_tables(new_tables, f"Jembatan L={L_val:.0f}m (Truk x={x_val:.1f}m, P={P_val:.0f}kN)")
            ss.redirect_page = "🏗️ Perhitungan Portal 2D"
            st.success("Model berhasil dikonversi dan dialihkan ke menu Perhitungan Portal 2D!")
            st.rerun()
            
    with mv_tabs[3]:
        st.markdown(r"""
### 📘 Dasar Teori Beban Bergerak pada Jembatan Sederhana

Pada balok sederhana di atas tumpuan sendi (kiri, $x=0$) dan rol (kanan, $x=L$) yang dilewati beban titik bergerak $P$ pada koordinat $x$:

#### 1. Keseimbangan Statika & Reaksi Tumpuan
Dari $\sum M_{\text{kanan}} = 0$:
$$R_1 \cdot L - P \cdot (L - x) = 0 \implies R_1(x) = \frac{P\,(L - x)}{L}$$

Dari $\sum M_{\text{kiri}} = 0$:
$$R_2 \cdot L - P \cdot x = 0 \implies R_2(x) = \frac{P\,x}{L}$$

Total keseimbangan gaya vertikal $\sum F_y = 0$:
$$R_1(x) + R_2(x) = \frac{P\,(L - x)}{L} + \frac{P\,x}{L} = P$$

#### 2. Momen Lentur di Bawah Beban (The Growing Graph)
Momen lentur tepat di bawah posisi truk dihitung dari potongan sebelah kiri:
$$M(x) = R_1(x) \cdot x = \frac{P\,x\,(L - x)}{L}$$
Grafik ini membentuk kurva parabola simetris dengan puncak di tengah bentang.

#### 3. Momen Maksimum Absolut
Untuk mencari posisi kritis $x$ yang menghasilkan momen terbesar sepanjang bentang:
$$\frac{dM(x)}{dx} = \frac{P}{L}(L - 2x) = 0 \implies x = \frac{L}{2}$$
Substitusikan $x = L/2$ ke dalam persamaan momen:
$$M_{\max} = \frac{P \cdot (L/2) \cdot (L/2)}{L} = \frac{P\,L}{4}$$
Untuk jembatan bentang $L = 20\text{ m}$ dan truk $P = 100\text{ kN}$:
$$M_{\max} = \frac{100 \times 20}{4} = 500\text{ kN}\cdot\text{m}$$
Sesuai dengan nilai puncak pada skala sumbu Y grafik ($0, 250, 500\text{ kN}\cdot\text{m}$).
""")
