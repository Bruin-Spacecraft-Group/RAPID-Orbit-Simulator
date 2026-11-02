"""
Full Orbital version of the sun_viz script, CZML output (CesiumJS)

Satellite data uses the python-sgp4 implementation by Brandon Rhodes

TLE data is still just ISS pulled from celestrak

Propagates one full orbit from the input TLE and writes a CZML document of the
full orbit (satellite, orbit path, altitude stem, sat->Sun vector, Earth->Sun
direction, North vector) and hands it to output.publish_czml, which writes a
standalone CesiumJS HTML viewer (CZML embedded) for GitHub Pages and opens it
locally.

Frame note: positions are written with referenceFrame "INERTIAL" (Cesium's ICRF).
SGP4 outputs TEME, which differs from ICRF by a small fixed-ish rotation
(a fraction of a degree today). That is fine for visualisation; if you need
exact alignment, rotate TEME -> ICRF with astropy/skyfield before calling build_czml.
"""

import sys
from pathlib import Path

import numpy as np
from sgp4.api import Satrec
from output import publish_czml
from czml import build_czml

# Allows us to import sun_model code
# sun_viz.py -> earth_models -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "submodules" / "RAPID-Software" / "src" / "lib"))

from sun_model import vec_satellite_to_sun

# ISS from Celestrak
EX_TLE1 = "1 25544U 98067A   26305.53114906  .00006056  00000+0  11739-3 0  9995"
EX_TLE2 = "2 25544  51.6332 340.4448 0007086 335.8887  24.1768 15.49140542593046"

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

def sat_to_sun_series(jd, fr, r_teme):
    """helper function that generates the final dataset"""
    sat_to_sun = np.array([vec_satellite_to_sun(j, f, r)
                           for j, f, r in zip(jd, fr, r_teme)])
    sun_xyz = r_teme + sat_to_sun      # recover Earth->Sun
    return sun_xyz

def sun_orbit_test():
    """Test script that shows the TLE's full orbit"""
    name = "Sun Vector (Cesium)"
    t_min, jd, fr, r_teme = propagate_orbit(EX_TLE1, EX_TLE2, n_steps=180)
    sun_xyz = sat_to_sun_series(jd, fr, r_teme)
    packets = build_czml(t_min, jd, fr, r_teme, sun_xyz, name=name)
    publish_czml(packets, name, out_dir="sun_models")

if __name__ == "__main__":
    sun_orbit_test()
