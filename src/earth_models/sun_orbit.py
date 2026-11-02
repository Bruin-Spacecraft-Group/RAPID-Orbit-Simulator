"""
Full Orbital version of the sun_viz script

Propagates one full orbit from the input TLE and visualises the time series data of the full orbit
using plotly
"""

import numpy as np
import plotly.graph_objects as go
from sgp4.api import Satrec
from output import publish

# Allows us to import sun_model code
import sys
from pathlib import Path

# sun_viz.py -> earth_models -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "submodules" / "RAPID-Software" / "src" / "lib"))

from sun_model import vec_satellite_to_sun

# Global helper variables
EX_TLE1 =  "1 25544U 98067A   26305.53114906  .00006056  00000+0  11739-3 0  9995"
EX_TLE2 = "2 25544  51.6332 340.4448 0007086 335.8887  24.1768 15.49140542593046"

R_EARTH = 6371.0  # km

def propagate_orbit(line1, line2, n_steps=120, n_orbits=1.0):
    """Return t_min (N,), jd (N,), fr (N,), r_teme (N,3) in km over n_orbits."""
    satrec = Satrec.twoline2rv(line1, line2)
    period_min = 2 * np.pi / satrec.no_kozai
    t_min = np.linspace(0.0, n_orbits * period_min, n_steps)

    jd = np.full(n_steps, satrec.jdsatepoch)
    fr = satrec.jdsatepochF + t_min / 1440.0
    err, r, _ = satrec.sgp4_array(jd, fr)
    if np.any(err):
        raise RuntimeError(f"SGP4 failed with error code {err}")
    return t_min, jd, fr, r

def _arrow_traces(start, vec, color, name, width=6, legend=True):
    end = start + vec
    d = vec / np.linalg.norm(vec)
    line = go.Scatter3d(
        x=[start[0], end[0]], y=[start[1], end[1]], z=[start[2], end[2]],
        mode="lines", line=dict(color=color, width=width),
        name=name, legendgroup=name, showlegend=legend, hoverinfo="skip")
    cone = go.Cone(
        x=[end[0]], y=[end[1]], z=[end[2]], u=[d[0]], v=[d[1]], w=[d[2]],
        anchor="tip", sizemode="absolute", sizeref=0.18 * np.linalg.norm(vec),
        colorscale=[[0, color], [1, color]], showscale=False,
        legendgroup=name, showlegend=False, hoverinfo="skip")
    return [line, cone]

def _geometry(sat_xyz, sun_xyz, R):
    sat_to_sun = sun_xyz - sat_xyz
    u = sat_to_sun / np.linalg.norm(sat_to_sun)
    r_sat = np.linalg.norm(sat_xyz)
    zenith = sat_xyz / r_sat
    angle = np.degrees(np.arccos(np.clip(u @ zenith, -1, 1)))
    return u, zenith, r_sat - R, angle

def _instant_traces(sat_xyz, sun_xyz, R, L):
    """The 6 traces that change every frame (order matters for frame updates)."""
    u, zenith, alt, angle = _geometry(sat_xyz, sun_xyz, R)
    foot = zenith * R
    stem = go.Scatter3d(
        x=[foot[0], sat_xyz[0]], y=[foot[1], sat_xyz[1]], z=[foot[2], sat_xyz[2]],
        mode="lines", line=dict(color="white", width=4, dash="dash"),
        name="altitude", hoverinfo="skip")
    marker = go.Scatter3d(
        x=[sat_xyz[0]], y=[sat_xyz[1]], z=[sat_xyz[2]], mode="markers",
        marker=dict(size=7, color="crimson", line=dict(color="white", width=1)),
        name="satellite")
    s_hat = sun_xyz / np.linalg.norm(sun_xyz)
    traces = ([stem, marker]
              + _arrow_traces(sat_xyz, u * L, "gold", "sat → Sun", 7)
              + _arrow_traces(np.zeros(3), s_hat * 2 * R, "red",
                              "Earth → Sun (direction)", 4))
    title = (f"altitude {alt:.1f} km · angle between sat→Sun and "
             f"local zenith: {angle:.1f}°")
    return traces, title, angle

def plot_orbit(t_min, sat_xyz, sun_xyz, R=R_EARTH, show=True):
    N, L = len(t_min), R
    fig = go.Figure()

    # --- static traces (indices 0, 1) ---
    a = np.linspace(0, 2 * np.pi, 60)
    b = np.linspace(0, np.pi, 30)

    fig.add_trace(go.Surface(
        x=R * np.outer(np.cos(a), np.sin(b)),
        y=R * np.outer(np.sin(a), np.sin(b)),
        z=R * np.outer(np.ones_like(a), np.cos(b)),
        colorscale=[[0, "#2b5fbf"], [1, "#2b5fbf"]], showscale=False,
        lighting=dict(ambient=0.55, diffuse=0.8, specular=0.1, roughness=0.9),
        hoverinfo="skip", name="Earth"))
    fig.add_trace(go.Scatter3d(
        x=sat_xyz[:, 0], y=sat_xyz[:, 1], z=sat_xyz[:, 2], mode="lines",
        line=dict(color="rgba(220,220,220,0.6)", width=3), name="orbit",
        hoverinfo="skip"))
    # North vector: from the north pole outward along +z
    north_len = 0.7 * R
    pole = np.array([0.0, 0.0, R])
    for tr in _arrow_traces(pole, np.array([0.0, 0.0, north_len]),
                            "limegreen", "North (+z)", width=6):
        fig.add_trace(tr)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[R + north_len * 1.25], mode="text", text=["N"],
        textfont=dict(color="limegreen", size=16),
        showlegend=False, hoverinfo="skip"))

    # --- dynamic traces: initial state + one frame per time step ---
    first, title0, _ = _instant_traces(sat_xyz[0], sun_xyz[0], R, L)
    for tr in first:
        fig.add_trace(tr)
    dyn_idx = list(range(2, 2 + len(first)))

    frames = []
    for i in range(N):
        tr, title, _ = _instant_traces(sat_xyz[i], sun_xyz[i], R, L)
        frames.append(go.Frame(data=tr, traces=dyn_idx, name=str(i),
                               layout=dict(title_text=title)))
    fig.frames = frames

    # --- controls ---
    play = dict(frame=dict(duration=100, redraw=True),
            transition=dict(duration=0),
            fromcurrent=True)
    steps = [dict(method="animate", label=f"{t:.0f}",
                  args=[[str(i)], dict(mode="immediate",
                                       frame=dict(duration=0, redraw=True))])
             for i, t in enumerate(t_min)]
    lim = 2.4 * R
    ax = dict(range=[-lim, lim], showbackground=False, zeroline=False,
              gridcolor="rgba(150,150,150,0.3)")
    fig.update_layout(
        title=title0,
        uirevision="keep",
        scene=dict(xaxis=dict(title="x (km)", **ax), yaxis=dict(title="y (km)", **ax),
                zaxis=dict(title="z (km)", **ax), aspectmode="cube",
                uirevision="keep"),
        updatemenus=[dict(type="buttons", x=0.05, y=0.02, buttons=[
            dict(label="Play", method="animate", args=[None, play]),
            dict(label="Pause", method="animate",
                 args=[[None], dict(mode="immediate",
                                    frame=dict(duration=0, redraw=False))])])],
        template = "plotly_dark",
        sliders=[dict(active=0, steps=steps, x=0.15, len=0.8,
                      currentvalue=dict(prefix="t (min since epoch): "))],
        legend=dict(x=0.01, y=0.99), margin=dict(l=0, r=0, t=50, b=0))
    if show:
        fig.show()
    return fig

def sat_to_sun_series(jd, fr, r_teme):
    """helper function that generates the final dataset"""
    sat_to_sun = np.array([vec_satellite_to_sun(j, f, r)
                           for j, f, r in zip(jd, fr, r_teme)])
    sun_xyz = r_teme + sat_to_sun      # recover Earth->Sun, since plot_sat_sun wants `sun`
    return sun_xyz

def sun_orbit_test():
    """Test script that shows the TLE's full orbit"""
    t_min, jd, fr, r_teme = propagate_orbit(EX_TLE1, EX_TLE2, n_steps=180)
    sun_xyz = sat_to_sun_series(jd, fr, r_teme)
    fig = plot_orbit(t_min, r_teme, sun_xyz, show=False)
    publish(fig, "Sun Vector (Full Orbit)")
    
if __name__ == "__main__":
    sun_orbit_test()
