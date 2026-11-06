"""Modul Analisis Beban Bergerak (Moving Load) & Visualisasi Interaktif.

Menyediakan:
1. Perhitungan analitis reaksi tumpuan, momen lentur, bidang geser & momen (SFD/BMD), serta garis pengaruh.
2. Komponen interaktif HTML5/SVG/JS (animasi 60 FPS, mobil dapat digerakkan/diseret langsung dengan mouse/touch).
3. Ekspor ke model portal 2D Structura untuk analisis metode kekakuan langsung.
"""
import json
import numpy as np
import plotly.graph_objects as go


def reactions(L, P, x):
    """Reaksi tumpuan sendi R1 (kiri) dan rol R2 (kanan) untuk beban titik P pada jarak x dari tumpuan kiri."""
    x_clamped = np.clip(x, 0.0, L)
    R1 = P * (L - x_clamped) / L
    R2 = P * x_clamped / L
    return float(R1), float(R2)


def moment_under_load(L, P, x):
    """Momen lentur tepat di bawah beban bergerak P: M(x) = P * x * (L - x) / L."""
    x_clamped = np.clip(x, 0.0, L)
    return float(P * x_clamped * (L - x_clamped) / L)


def beam_diagrams(L, P, x, n_pts=201):
    """Menghitung distribusi gaya geser V(z) dan momen lentur M(z) di sepanjang bentang balok z in [0, L]

    untuk posisi beban saat ini x. Menyertakan titik diskontinuitas di x- dan x+.
    """
    R1, R2 = reactions(L, P, x)
    x_c = float(np.clip(x, 0.0, L))
    eps = 1e-6
    z_base = np.linspace(0, L, n_pts)
    z_extra = [max(0.0, x_c - eps), x_c, min(L, x_c + eps)]
    z = np.unique(np.sort(np.concatenate([z_base, z_extra])))
    V = np.where(z < x_c, R1, np.where(z > x_c, -R2, 0.0))
    M = np.where(z <= x_c, R1 * z, R2 * (L - z))
    return z, V, M


def max_moment_envelope(L, P, n_pts=201):
    """Menghitung selubung momen lentur maksimum absolut di sepanjang bentang balok.

    Untuk beban titik tunggal pada balok sederhana, selubung momen maksimum pada titik z adalah:
    M_maks(z) = P * z * (L - z) / L.
    """
    z = np.linspace(0, L, n_pts)
    M_env = P * z * (L - z) / L
    return z, M_env


def influence_lines(L, section_c, n_pts=201):
    """Garis pengaruh reaksi R1, R2, geser V_c, dan momen M_c pada potongan z = section_c."""
    x = np.linspace(0, L, n_pts)
    il_R1 = (L - x) / L
    il_R2 = x / L
    il_Vc = np.where(x < section_c, -x / L, (L - x) / L)
    il_Mc = np.where(x <= section_c, x * (L - section_c) / L, section_c * (L - x) / L)
    return x, il_R1, il_R2, il_Vc, il_Mc


def to_structura_model(L, P, x, num_elements=10, E=200000.0, b=300.0, h=600.0):
    """Mengonversi balok sederhana dengan beban titik di posisi x menjadi model portal 2D

    yang kompatibel dengan mesin analisis matriks Structura (`structura.engine`).
    """
    L = float(L)
    P = float(P)
    x = float(np.clip(x, 0.01 * L, 0.99 * L))

    xs = sorted(list(set(list(np.linspace(0, L, num_elements + 1)) + [x])))
    nodes = [{"id": i + 1, "x": float(round(xi, 4)), "y": 0.0} for i, xi in enumerate(xs)]

    target_node = min(nodes, key=lambda n: abs(n["x"] - x))["id"]

    members = []
    for i in range(len(nodes) - 1):
        members.append({
            "id": i + 1,
            "ni": nodes[i]["id"],
            "nj": nodes[i + 1]["id"],
            "E": float(E),
            "b": float(b),
            "h": float(h)
        })

    supports = [
        {"node": 1, "ux": True, "uy": True, "rz": False},
        {"node": len(nodes), "ux": False, "uy": True, "rz": False}
    ]

    nodal_loads = [
        {"node": target_node, "Fx": 0.0, "Fy": -P, "M": 0.0}
    ]

    return {
        "nodes": nodes,
        "members": members,
        "supports": supports,
        "nodal_loads": nodal_loads,
        "member_loads": []
    }


def plotly_diagrams_figure(L, P, x):
    """Menghasilkan figure Plotly untuk SFD dan BMD seketika pada posisi x saat ini."""
    z, V, M = beam_diagrams(L, P, x)
    R1, R2 = reactions(L, P, x)
    M_curr = moment_under_load(L, P, x)
    z_env, M_env = max_moment_envelope(L, P)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=z, y=M, mode="lines", name=f"Momen M(z) saat x={x:.2f}m",
        line=dict(color="#1971c2", width=3),
        fill="tozeroy", fillcolor="rgba(25, 113, 194, 0.15)"
    ))
    fig.add_trace(go.Scatter(
        x=z_env, y=M_env, mode="lines", name="Selubung M_maks (Envelope)",
        line=dict(color="#7950f2", width=2, dash="dash")
    ))
    fig.add_trace(go.Scatter(
        x=[x], y=[M_curr], mode="markers+text", name="Titik Beban",
        marker=dict(size=10, color="#e03131"),
        text=[f"M={M_curr:.1f} kNm"], textposition="top center"
    ))

    fig.update_layout(
        title=f"Diagram Momen Lentur BMD (Posisi Truk x = {x:.2f} m, R₁ = {R1:.1f} kN, R₂ = {R2:.1f} kN)",
        xaxis_title="Panjang Balok z (m)",
        yaxis_title="Momen Lentur M (kN·m)",
        hovermode="x unified",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def plotly_sfd_figure(L, P, x):
    """Menghasilkan figure Plotly untuk SFD (Bidang Gaya Geser)."""
    z, V, _ = beam_diagrams(L, P, x)
    R1, R2 = reactions(L, P, x)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=z, y=V, mode="lines", name=f"Gaya Geser V(z) saat x={x:.2f}m",
        line=dict(color="#e8590c", width=3),
        fill="tozeroy", fillcolor="rgba(232, 89, 12, 0.15)"
    ))

    fig.update_layout(
        title=f"Diagram Gaya Geser SFD (R₁ = +{R1:.1f} kN, R₂ = +{R2:.1f} kN)",
        xaxis_title="Panjang Balok z (m)",
        yaxis_title="Gaya Geser V (kN)",
        hovermode="x unified",
        height=340,
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def render_moving_load_html(L=20.0, P=100.0, initial_x=4.6, vehicle_type="truck"):
    """Menghasilkan kode HTML/CSS/JS mandiri interaktif di mana pengguna dapat menggeser/menyeret

    mobil secara langsung (drag & drop), dengan teks yang rapi dan nilai beban P yang selalu sinkron.
    """
    config = {
        "L": float(L),
        "P": float(P),
        "initial_x": float(initial_x),
        "vehicle_type": str(vehicle_type)
    }
    cfg_json = json.dumps(config)
    p_formatted = f"{float(P):g}"

    html_template = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simulasi Beban Bergerak - Structura</title>
<style>
  :root {{
    --bg-main: #f8fafc;
    --card-bg: #ffffff;
    --border-color: #e2e8f0;
    --text-primary: #1e293b;
    --text-muted: #64748b;
    --bridge-teal: #38b2ac;
    --bridge-stroke: #1d7069;
    --truck-red: #dc2626;
    --support-pin: #2563eb;
    --support-roller: #7c3aed;
    --curve-purple: #6366f1;
    --curve-fill: rgba(99, 102, 241, 0.22);
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  }}

  body {{
    background-color: var(--bg-main);
    color: var(--text-primary);
    padding: 8px;
    display: flex;
    justify-content: center;
  }}

  .sim-container {{
    width: 100%;
    max-width: 960px;
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-radius: 20px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
    overflow: hidden;
  }}

  .sim-header {{
    text-align: center;
    padding: 20px 20px 6px 20px;
  }}

  .sim-header h2 {{
    font-family: "Georgia", "Cambria", serif;
    font-size: 26px;
    font-weight: 500;
    color: #1e293b;
    letter-spacing: -0.3px;
  }}

  .sim-header p {{
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 4px;
  }}

  /* Main Canvas Stage */
  .canvas-stage {{
    position: relative;
    width: 100%;
    height: 480px;
    background: #ffffff;
    overflow: hidden;
    user-select: none;
    -webkit-user-select: none;
  }}

  svg#simSvg {{
    width: 100%;
    height: 100%;
    display: block;
  }}

  /* Floating Math Card */
  .math-card {{
    position: absolute;
    right: 24px;
    bottom: 24px;
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(226, 232, 240, 0.95);
    border-radius: 14px;
    padding: 16px 22px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
    min-width: 290px;
    max-width: 340px;
    pointer-events: none;
  }}

  .math-card .card-title {{
    font-size: 14px;
    font-weight: 600;
    color: #475569;
    text-align: center;
    margin-bottom: 6px;
  }}

  .math-card .eq-balance {{
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
    text-align: center;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px dashed #cbd5e1;
    font-family: "Cambria Math", "Georgia", serif;
  }}

  .math-card .formula-box {{
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
    font-family: "Georgia", serif;
  }}

  .math-card .formula-box .fraction {{
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    vertical-align: middle;
    margin: 0 4px;
  }}

  .math-card .formula-box .numerator {{
    border-bottom: 1.5px solid #1e293b;
    padding: 0 4px 1px 4px;
    text-align: center;
  }}

  .math-card .formula-box .denominator {{
    padding: 1px 4px 0 4px;
    text-align: center;
  }}

  .math-card .calc-row {{
    font-size: 13.5px;
    color: #475569;
    margin-top: 4px;
    display: flex;
    justify-content: space-between;
    font-family: "Consolas", "Courier New", monospace;
  }}

  .math-card .calc-row strong {{
    color: #0f172a;
  }}

  /* Interactive Simulator Toolbar (Bukan Video) */
  .sim-toolbar {{
    background: #f8fafc;
    border-top: 1px solid var(--border-color);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }}

  .toolbar-left {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .toolbar-btn {{
    background: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }}

  .toolbar-btn:hover {{
    background: #f1f5f9;
    color: #0f172a;
    border-color: #94a3b8;
  }}

  .toolbar-btn.primary {{
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
  }}

  .toolbar-btn.primary:hover {{
    background: #1d4ed8;
  }}

  .slider-box {{
    flex: 1;
    min-width: 260px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .slider-label {{
    font-size: 13px;
    font-weight: 600;
    color: #475569;
    white-space: nowrap;
  }}

  .pos-slider {{
    -webkit-appearance: none;
    width: 100%;
    height: 8px;
    border-radius: 4px;
    background: #e2e8f0;
    outline: none;
    cursor: pointer;
  }}

  .pos-slider::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #2563eb;
    border: 2px solid #ffffff;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  }}

  .pos-display {{
    font-size: 14px;
    font-weight: 700;
    color: #1e293b;
    font-family: "Consolas", monospace;
    min-width: 95px;
    text-align: right;
  }}

  /* Truck Grab Styling */
  #truckGroup {{
    cursor: grab;
  }}
  #truckGroup:active {{
    cursor: grabbing;
  }}
</style>
</head>
<body>

<div class="sim-container">
  <!-- Header -->
  <div class="sim-header">
    <h2>A moving load. A growing graph.</h2>
    <p>💡 Seret mobil langsung di atas jembatan atau geser pengatur posisi di bawah untuk melihat perubahan momen & reaksi.</p>
  </div>

  <!-- Main Canvas Stage -->
  <div class="canvas-stage" id="stage">
    <svg id="simSvg" viewBox="0 0 960 480">
      <defs>
        <linearGradient id="purpleGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#7c3aed" stop-opacity="0.45"/>
          <stop offset="100%" stop-color="#7c3aed" stop-opacity="0.04"/>
        </linearGradient>

        <linearGradient id="bridgeGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#4fd1c5"/>
          <stop offset="100%" stop-color="#319795"/>
        </linearGradient>

        <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.15"/>
        </filter>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur"/>
          <feComposite in="SourceGraphic" in2="blur" operator="over"/>
        </filter>
      </defs>

      <!-- ================= BRIDGE STRUCTURE (Y = 110 to 138) ================= -->
      <g id="bridgeGroup">
        <!-- Chords Background: Deck Y=110, Bottom Y=138 (Height=28px) -->
        <rect x="80" y="110" width="760" height="28" rx="2" fill="url(#bridgeGrad)" stroke="#1d7069" stroke-width="2.2"/>
        <g id="trussWeb" stroke="#134e48" stroke-width="2" stroke-linecap="round"></g>
        <line x1="75" y1="110" x2="845" y2="110" stroke="#0f766e" stroke-width="3"/>
      </g>

      <!-- Left Support: Pin Support at X=120, Y=138 -->
      <g id="leftSupport" transform="translate(120, 138)">
        <polygon points="0,0 -18,24 18,24" fill="#ffffff" stroke="#2563eb" stroke-width="2.5"/>
        <circle cx="0" cy="0" r="4.5" fill="#2563eb"/>
        <line x1="-24" y1="24" x2="24" y2="24" stroke="#1e40af" stroke-width="3"/>
        <g stroke="#94a3b8" stroke-width="1.8">
          <line x1="-20" y1="24" x2="-26" y2="31"/>
          <line x1="-12" y1="24" x2="-18" y2="31"/>
          <line x1="-4" y1="24" x2="-10" y2="31"/>
          <line x1="4" y1="24" x2="-2" y2="31"/>
          <line x1="12" y1="24" x2="6" y2="31"/>
          <line x1="20" y1="24" x2="14" y2="31"/>
        </g>
        <!-- Reaction R1 Arrow (Upward) & Label: Y = 28 to 72, Label at Y = 84 (X=120, Y=222 global) -->
        <g id="arrowR1Group">
          <line id="arrowR1Line" x1="0" y1="68" x2="0" y2="29" stroke="#2563eb" stroke-width="3.5"/>
          <polygon points="0,26 -5,36 5,36" fill="#2563eb"/>
          <text id="labelR1" x="0" y="84" text-anchor="middle" font-size="14" font-weight="700" fill="#1d4ed8" font-family="'Consolas', monospace">R₁ = 77.0 kN</text>
        </g>
      </g>

      <!-- Right Support: Roller Support at X=800, Y=138 -->
      <g id="rightSupport" transform="translate(800, 138)">
        <polygon points="0,0 -18,20 18,20" fill="#ffffff" stroke="#7c3aed" stroke-width="2.5"/>
        <circle cx="0" cy="0" r="4.5" fill="#7c3aed"/>
        <circle cx="-8" cy="24" r="3.5" fill="#ffffff" stroke="#7c3aed" stroke-width="2.2"/>
        <circle cx="8" cy="24" r="3.5" fill="#ffffff" stroke="#7c3aed" stroke-width="2.2"/>
        <line x1="-24" y1="28" x2="24" y2="28" stroke="#6d28d9" stroke-width="3"/>
        <!-- Reaction R2 Arrow & Label -->
        <g id="arrowR2Group">
          <line id="arrowR2Line" x1="0" y1="68" x2="0" y2="32" stroke="#7c3aed" stroke-width="3.5"/>
          <polygon points="0,29 -5,39 5,39" fill="#7c3aed"/>
          <text id="labelR2" x="0" y="84" text-anchor="middle" font-size="14" font-weight="700" fill="#6d28d9" font-family="'Consolas', monospace">R₂ = 23.0 kN</text>
        </g>
      </g>

      <!-- Dimension Line for x (Y = 175, Text at Y = 195) -->
      <g id="dimGroup">
        <line id="dimLine" x1="120" y1="175" x2="276" y2="175" stroke="#dc2626" stroke-width="2"/>
        <line x1="120" y1="168" x2="120" y2="182" stroke="#dc2626" stroke-width="2"/>
        <line id="dimTickRight" x1="276" y1="168" x2="276" y2="182" stroke="#dc2626" stroke-width="2"/>
        <text id="dimText" x="460" y="195" text-anchor="middle" font-size="14" font-weight="600" fill="#334155" font-family="'Consolas', monospace">x = 04.6 m &nbsp;/&nbsp; L = 20.0 m</text>
      </g>

      <!-- Moving Truck Vehicle (Directly Draggable!) -->
      <g id="truckGroup" transform="translate(276, 110)">
        <!-- Load Arrow P pointing down with DYNAMIC VALUE -->
        <g id="loadArrowP" transform="translate(0, -68)">
          <text id="loadPText" x="0" y="-12" text-anchor="middle" font-size="14.5" font-weight="700" fill="#dc2626" font-family="'Consolas', monospace">P = {p_formatted} kN</text>
          <line x1="0" y1="-8" x2="0" y2="12" stroke="#dc2626" stroke-width="3.5"/>
          <polygon points="0,15 -5,5 5,5" fill="#dc2626"/>
        </g>

        <!-- Truck Cargo Box -->
        <rect x="-56" y="-56" width="68" height="42" rx="4" fill="#f8fafc" stroke="#94a3b8" stroke-width="2.2" filter="url(#shadow)"/>
        <line x1="-50" y1="-35" x2="6" y2="-35" stroke="#e2e8f0" stroke-width="2"/>
        <rect x="-48" y="-48" width="52" height="10" rx="1.5" fill="#f1f5f9"/>

        <!-- Truck Cab -->
        <path d="M12 -14 L12 -44 L32 -44 Q36 -44 40 -38 L48 -24 Q52 -20 52 -14 L52 -14 Z" fill="#dc2626" stroke="#b91c1c" stroke-width="2.2" filter="url(#shadow)"/>
        <path d="M28 -40 L36 -40 L44 -26 L28 -26 Z" fill="#bae6fd" stroke="#0284c7" stroke-width="1.5"/>
        <rect x="48" y="-20" width="5" height="6" rx="1" fill="#facc15"/>
        <rect x="47" y="-14" width="7" height="4" rx="1" fill="#475569"/>

        <!-- Wheels (2 Axles) -->
        <g class="wheel" id="wheel1" transform="translate(-36, -12)">
          <circle cx="0" cy="0" r="9" fill="#1e293b" stroke="#0f172a" stroke-width="2"/>
          <circle cx="0" cy="0" r="4.5" fill="#94a3b8"/>
        </g>
        <g class="wheel" id="wheel2" transform="translate(32, -12)">
          <circle cx="0" cy="0" r="9" fill="#1e293b" stroke="#0f172a" stroke-width="2"/>
          <circle cx="0" cy="0" r="4.5" fill="#94a3b8"/>
        </g>
      </g>

      <!-- ================= GROWING GRAPH (BOTTOM LEFT, Y = 265 to 445) ================= -->
      <!-- Clean separation: Y = 265 is 43px below R1 label (Y = 222) -->
      <g id="graphGroup" transform="translate(0, 0)">
        <text x="95" y="262" font-size="14" font-weight="600" fill="#475569" font-family="'Georgia', serif">Bending moment as the truck moves</text>

        <!-- Y Axis Ticks & Gridlines -->
        <g stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3 3">
          <line x1="95" y1="430" x2="475" y2="430"/>
          <line x1="95" y1="355" x2="475" y2="355"/>
          <line x1="95" y1="280" x2="475" y2="280"/>
        </g>

        <!-- Axis Labels -->
        <text x="85" y="272" text-anchor="end" font-size="11.5" font-weight="600" fill="#64748b">kN·m</text>
        <text id="tickTop" x="85" y="284" text-anchor="end" font-size="11" fill="#64748b">500</text>
        <text id="tickMid" x="85" y="359" text-anchor="end" font-size="11" fill="#64748b">250</text>
        <text x="85" y="434" text-anchor="end" font-size="11" fill="#64748b">0</text>

        <!-- Main Axes -->
        <line x1="95" y1="275" x2="95" y2="430" stroke="#334155" stroke-width="2"/>
        <line x1="95" y1="430" x2="480" y2="430" stroke="#334155" stroke-width="2"/>

        <!-- Filled Growing Curve Area -->
        <path id="graphArea" d="M95,430 L95,430 Z" fill="url(#purpleGrad)"/>

        <!-- The Growing Graph Curve Line -->
        <path id="graphLine" d="M95,430" fill="none" stroke="#6366f1" stroke-width="3.5" stroke-linecap="round"/>

        <!-- Vertical Drop Line from current point to X-axis -->
        <line id="dropLine" x1="95" y1="430" x2="95" y2="430" stroke="#818cf8" stroke-width="1.8" stroke-dasharray="3 2"/>

        <!-- Active Dot Marker at (x, M) -->
        <circle id="graphDot" cx="95" cy="430" r="5" fill="#4f46e5" stroke="#ffffff" stroke-width="2" filter="url(#glow)"/>

        <!-- Theoretical Full Envelope (Ghost Outline) -->
        <path id="envelopeGhost" d="" fill="none" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 3"/>
      </g>
    </svg>

    <!-- Floating Math Card (Bottom Right) -->
    <div class="math-card" id="mathCard">
      <div class="card-title">The load stays balanced</div>
      <div class="eq-balance" id="eqBalanceText">R₁ + R₂ = P = {p_formatted} kN</div>
      <div class="formula-box">
        <span>M = </span>
        <div class="fraction">
          <span class="numerator">P × x × (L − x)</span>
          <span class="denominator">L</span>
        </div>
      </div>
      <div class="calc-row">
        <span>R₁ = P(L−x)/L:</span>
        <strong id="valR1Text">77.0 kN</strong>
      </div>
      <div class="calc-row">
        <span>R₂ = P·x/L:</span>
        <strong id="valR2Text">23.0 kN</strong>
      </div>
      <div class="calc-row" style="margin-top: 8px; border-top: 1px solid #f1f5f9; padding-top: 6px;">
        <span style="color:#4f46e5; font-weight:600;">M(x):</span>
        <strong id="valMText" style="color:#4f46e5; font-size:15px;">354.2 kN·m</strong>
      </div>
    </div>
  </div>

  <!-- Interactive Control Bar (Bukan Video!) -->
  <div class="sim-toolbar">
    <div class="toolbar-left">
      <button class="toolbar-btn primary" id="autoPlayBtn">
        <span id="playLabel">🚗 Jalankan Otomatis</span>
      </button>
      <button class="toolbar-btn" id="midspanBtn" title="Pindah ke posisi momen maksimum">
        <span>📍 Titik Tengah (x = L/2)</span>
      </button>
      <button class="toolbar-btn" id="resetBtn" title="Reset posisi ke awal">
        <span>🔄 Reset (x = 0)</span>
      </button>
    </div>

    <div class="slider-box">
      <span class="slider-label">Posisi Beban (x):</span>
      <input type="range" class="pos-slider" id="posSlider" min="0" max="1000" value="230">
      <span class="pos-display" id="posDisplay">04.6 / 20.0 m</span>
    </div>
  </div>
</div>

<script>
(function() {{
  const config = {cfg_json};
  const L = config.L || 20.0;
  const P = config.P || 100.0;
  let currentX = config.initial_x !== undefined ? config.initial_x : 4.6;
  let isAutoRunning = false;
  let animFrameId = null;
  let lastTimestamp = null;
  let isDragging = false;

  // Geometry Mapping
  // Left Support: X = 120, Right Support: X = 800 (Span = 680 px)
  const X_START = 120;
  const X_END = 800;
  const SPAN_PX = X_END - X_START;

  // Graph Mapping (Bottom Left)
  // Origin at (95, 430). Width = 380 px (X: 95 -> 475). Height = 150 px (Y: 430 -> 280)
  const G_X0 = 95;
  const G_W = 380;
  const G_Y0 = 430;
  const G_H = 150;
  const M_MAX_THEORETICAL = (P * L) / 4.0; // Peak at x = L/2

  // Update Dynamic Axis Ticks & Formula Card
  const tickTop = document.getElementById("tickTop");
  const tickMid = document.getElementById("tickMid");
  if (tickTop) tickTop.textContent = Math.round(M_MAX_THEORETICAL);
  if (tickMid) tickMid.textContent = Math.round(M_MAX_THEORETICAL / 2);

  const loadPText = document.getElementById("loadPText");
  if (loadPText) loadPText.textContent = `P = ${{P.toFixed(0)}} kN`;
  const eqBalanceText = document.getElementById("eqBalanceText");
  if (eqBalanceText) eqBalanceText.textContent = `R₁ + R₂ = P = ${{P.toFixed(0)}} kN`;

  // DOM Elements
  const simSvg = document.getElementById("simSvg");
  const truckGroup = document.getElementById("truckGroup");
  const bridgeGroup = document.getElementById("bridgeGroup");
  const dimLine = document.getElementById("dimLine");
  const dimTickRight = document.getElementById("dimTickRight");
  const dimText = document.getElementById("dimText");
  const arrowR1Line = document.getElementById("arrowR1Line");
  const labelR1 = document.getElementById("labelR1");
  const arrowR2Line = document.getElementById("arrowR2Line");
  const labelR2 = document.getElementById("labelR2");
  const valR1Text = document.getElementById("valR1Text");
  const valR2Text = document.getElementById("valR2Text");
  const valMText = document.getElementById("valMText");
  const graphLine = document.getElementById("graphLine");
  const graphArea = document.getElementById("graphArea");
  const graphDot = document.getElementById("graphDot");
  const dropLine = document.getElementById("dropLine");
  const envelopeGhost = document.getElementById("envelopeGhost");
  const autoPlayBtn = document.getElementById("autoPlayBtn");
  const playLabel = document.getElementById("playLabel");
  const midspanBtn = document.getElementById("midspanBtn");
  const resetBtn = document.getElementById("resetBtn");
  const posSlider = document.getElementById("posSlider");
  const posDisplay = document.getElementById("posDisplay");

  // Build Truss Web Geometry (Warren Truss)
  function initTruss() {{
    const truss = document.getElementById("trussWeb");
    if (!truss) return;
    let d = "";
    const numPanels = 38;
    const dx = 760 / numPanels;
    let x = 80;
    let up = true;
    for (let i = 0; i < numPanels; i++) {{
      const xNext = x + dx;
      const y1 = up ? 138 : 110;
      const y2 = up ? 110 : 138;
      d += `M${{x.toFixed(1)}},${{y1}} L${{xNext.toFixed(1)}},${{y2}} `;
      up = !up;
      x = xNext;
    }}
    truss.setAttribute("d", d);

    // Theoretical Envelope Path
    let ghostD = `M${{G_X0}},${{G_Y0}}`;
    for (let i = 0; i <= 60; i++) {{
      const xi = (i / 60) * L;
      const mi = (P * xi * (L - xi)) / L;
      const gx = G_X0 + (xi / L) * G_W;
      const gy = G_Y0 - (mi / (M_MAX_THEORETICAL || 1)) * G_H;
      ghostD += ` L${{gx.toFixed(1)}},${{gy.toFixed(1)}}`;
    }}
    if (envelopeGhost) envelopeGhost.setAttribute("d", ghostD);
  }}
  initTruss();

  // Core Update Function
  function update(xVal) {{
    currentX = Math.max(0, Math.min(L, xVal));

    // Physics calculations
    const R1 = P * (L - currentX) / L;
    const R2 = P * currentX / L;
    const M = P * currentX * (L - currentX) / L;

    // 1. Position Truck
    const truckPxX = X_START + (currentX / L) * SPAN_PX;
    if (truckGroup) {{
      truckGroup.setAttribute("transform", `translate(${{truckPxX}}, 110)`);
    }}

    // 2. Dimension Line
    if (dimLine) {{
      dimLine.setAttribute("x2", truckPxX);
      dimTickRight.setAttribute("x1", truckPxX);
      dimTickRight.setAttribute("x2", truckPxX);
      const xStr = currentX < 10 ? "0" + currentX.toFixed(1) : currentX.toFixed(1);
      dimText.textContent = `x = ${{xStr}} m   /   L = ${{L.toFixed(1)}} m`;
    }}

    // 3. Reactions & Arrows
    if (labelR1) labelR1.textContent = `R₁ = ${{R1.toFixed(1)}} kN`;
    if (labelR2) labelR2.textContent = `R₂ = ${{R2.toFixed(1)}} kN`;
    const maxArrowH = 40;
    const h1 = 15 + (R1 / (P || 1)) * maxArrowH;
    const h2 = 15 + (R2 / (P || 1)) * maxArrowH;
    if (arrowR1Line) arrowR1Line.setAttribute("y1", 26 + h1);
    if (arrowR2Line) arrowR2Line.setAttribute("y1", 28 + h2);

    // 4. Math Card
    if (valR1Text) valR1Text.textContent = `${{R1.toFixed(1)}} kN`;
    if (valR2Text) valR2Text.textContent = `${{R2.toFixed(1)}} kN`;
    if (valMText) valMText.textContent = `${{M.toFixed(1)}} kN·m`;

    // 5. Growing Graph
    const currGx = G_X0 + (currentX / L) * G_W;
    const currGy = G_Y0 - (M / (M_MAX_THEORETICAL || 1)) * G_H;

    const steps = Math.max(2, Math.round((currentX / L) * 60));
    let pathD = `M${{G_X0}},${{G_Y0}}`;
    let areaD = `M${{G_X0}},${{G_Y0}}`;

    for (let i = 1; i <= steps; i++) {{
      const xi = (i / steps) * currentX;
      const mi = (P * xi * (L - xi)) / L;
      const gx = G_X0 + (xi / L) * G_W;
      const gy = G_Y0 - (mi / (M_MAX_THEORETICAL || 1)) * G_H;
      pathD += ` L${{gx.toFixed(1)}},${{gy.toFixed(1)}}`;
      areaD += ` L${{gx.toFixed(1)}},${{gy.toFixed(1)}}`;
    }}
    areaD += ` L${{currGx.toFixed(1)}},${{G_Y0}} Z`;

    if (graphLine) graphLine.setAttribute("d", pathD);
    if (graphArea) graphArea.setAttribute("d", areaD);
    if (graphDot) {{
      graphDot.setAttribute("cx", currGx);
      graphDot.setAttribute("cy", currGy);
    }}
    if (dropLine) {{
      dropLine.setAttribute("x1", currGx);
      dropLine.setAttribute("y1", currGy);
      dropLine.setAttribute("x2", currGx);
      dropLine.setAttribute("y2", G_Y0);
    }}

    // 6. UI Slider & Position Text
    if (posSlider && document.activeElement !== posSlider) {{
      posSlider.value = Math.round((currentX / L) * 1000);
    }}
    const xFmt = currentX < 10 ? "0" + currentX.toFixed(1) : currentX.toFixed(1);
    if (posDisplay) {{
      posDisplay.textContent = `${{xFmt}} / ${{L.toFixed(1)}} m`;
    }}
  }}

  // ================= DIRECT DRAGGING OF TRUCK =================
  function getSvgPoint(e) {{
    const pt = simSvg.createSVGPoint();
    if (e.touches && e.touches.length > 0) {{
      pt.x = e.touches[0].clientX;
      pt.y = e.touches[0].clientY;
    }} else {{
      pt.x = e.clientX;
      pt.y = e.clientY;
    }}
    return pt.matrixTransform(simSvg.getScreenCTM().inverse());
  }}

  if (truckGroup) {{
    truckGroup.addEventListener("mousedown", function(e) {{
      e.preventDefault();
      isDragging = true;
      if (isAutoRunning) stopAuto();
    }});

    truckGroup.addEventListener("touchstart", function(e) {{
      isDragging = true;
      if (isAutoRunning) stopAuto();
    }}, {{passive: true}});
  }}

  // Allow clicking on bridge to move truck
  if (bridgeGroup) {{
    bridgeGroup.style.cursor = "pointer";
    bridgeGroup.addEventListener("click", function(e) {{
      const p = getSvgPoint(e);
      const frac = (p.x - X_START) / SPAN_PX;
      currentX = Math.max(0, Math.min(1, frac)) * L;
      update(currentX);
    }});
  }}

  window.addEventListener("mousemove", function(e) {{
    if (!isDragging) return;
    const p = getSvgPoint(e);
    const frac = (p.x - X_START) / SPAN_PX;
    currentX = Math.max(0, Math.min(1, frac)) * L;
    update(currentX);
  }});

  window.addEventListener("touchmove", function(e) {{
    if (!isDragging) return;
    const p = getSvgPoint(e);
    const frac = (p.x - X_START) / SPAN_PX;
    currentX = Math.max(0, Math.min(1, frac)) * L;
    update(currentX);
  }}, {{passive: true}});

  window.addEventListener("mouseup", function() {{ isDragging = false; }});
  window.addEventListener("touchend", function() {{ isDragging = false; }});

  // Slider change
  if (posSlider) {{
    posSlider.addEventListener("input", function() {{
      if (isAutoRunning) stopAuto();
      const frac = parseFloat(this.value) / 1000.0;
      currentX = frac * L;
      update(currentX);
    }});
  }}

  // Jump to midspan
  if (midspanBtn) {{
    midspanBtn.addEventListener("click", function() {{
      if (isAutoRunning) stopAuto();
      currentX = L / 2.0;
      update(currentX);
    }});
  }}

  // Reset
  if (resetBtn) {{
    resetBtn.addEventListener("click", function() {{
      if (isAutoRunning) stopAuto();
      currentX = 0.0;
      update(currentX);
    }});
  }}

  // Auto Run Feature
  function autoTick(timestamp) {{
    if (!lastTimestamp) lastTimestamp = timestamp;
    const delta = (timestamp - lastTimestamp) / 1000;
    lastTimestamp = timestamp;

    if (isAutoRunning) {{
      const speedMps = L / 8.0; // 8 seconds crossing
      currentX += speedMps * delta;
      if (currentX >= L) {{
        currentX = L;
        stopAuto();
      }}
      update(currentX);
    }}

    if (isAutoRunning) {{
      animFrameId = requestAnimationFrame(autoTick);
    }}
  }}

  function stopAuto() {{
    isAutoRunning = false;
    if (playLabel) playLabel.textContent = "🚗 Jalankan Otomatis";
    if (animFrameId) cancelAnimationFrame(animFrameId);
  }}

  function startAuto() {{
    if (currentX >= L) currentX = 0.0;
    isAutoRunning = true;
    lastTimestamp = null;
    if (playLabel) playLabel.textContent = "⏸ Jeda";
    animFrameId = requestAnimationFrame(autoTick);
  }}

  if (autoPlayBtn) {{
    autoPlayBtn.addEventListener("click", function() {{
      if (isAutoRunning) stopAuto();
      else startAuto();
    }});
  }}

  // Initial draw
  update(currentX);
}})();
</script>
</body>
</html>
"""
    return html_template


# Alias untuk kompatibilitas
render_thetawise_html = render_moving_load_html
