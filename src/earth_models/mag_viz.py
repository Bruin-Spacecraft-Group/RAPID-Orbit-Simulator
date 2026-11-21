"""Render magnetic-field vectors along an example satellite orbit with CesiumJS.

The script propagates an ISS orbit, calculates the magnetic field at each
satellite position, and publishes the orbit and field vectors as CZML.

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
from czml import build_czml, R_EARTH

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import TEME, ITRS, CartesianRepresentation

# Allows us to import sun_model code
# sun_viz.py -> earth_models -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "submodules" / "RAPID-Software" / "src" / "lib"))

from sun_model import vec_satellite_to_sun
from pygeomag import GeoMag
from pygeomag.wmm.wmm_2025 import WMM_2025

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

def sat_to_mag_series(jd, fr, r_teme): #change function
    """helper function that generates the final dataset"""

    geo_mag = GeoMag(coefficients_file="wmm/WMM_2025.COF")

    t = Time(jd, fr, format='jd', scale='utc')

    r = np.atleast_2d(r_teme).T                      # -> (3, N)
    teme = TEME(CartesianRepresentation(r * u.km), obstime=t)
    itrs = teme.transform_to(ITRS(obstime=t))

    loc = itrs.earth_location                        # WGS84 by default
    glat = loc.lat.deg                               # geodetic latitude, deg
    glon = loc.lon.deg                               # east longitude, -180..180
    alt  = loc.height.to(u.km).value                 # altitude above ellipsoid, km
    try:
        time = float(t.utc.iso)                     # or t.utc.iso
    except Exception:
        time = np.atleast_1d(t.utc.decimalyear)

    #sat_to_mag_original = np.array([vec_satellite_to_sun(j, f, r)
                           #for j, f, r in zip(jd, fr, r_teme)])

    # two calculates to get xyz components
    mag_xyz = []
    for glat0, glon0, alt0, time0 in zip(glat, glon, alt, time):
        mag = geo_mag.calculate(glat0, glon0, alt0, time0)
        mag.calculate(False)
        mag_xyz.append([mag.x, mag.y, mag.z])

    np.array(mag_xyz)

    return mag_xyz

def mag_orbit_test():
    """Test script that shows the TLE's full orbit"""
    name = "Magnetic Field Vector (Cesium)"
    t_min, jd, fr, r_teme = propagate_orbit(EX_TLE1, EX_TLE2, n_steps=180)
    mag_xyz = np.asarray(sat_to_mag_series(jd, fr, r_teme), dtype=float)
    mag_norm = np.linalg.norm(mag_xyz, axis=1, keepdims=True)
    mag_direction = np.divide(
        mag_xyz,
        mag_norm,
        out=np.zeros_like(mag_xyz),
        where=mag_norm != 0,
    )
    vectors = [(mag_direction * R_EARTH, r_teme)]
    packets = build_czml(t_min, jd, fr, r_teme, vectors, name=name)
    publish_czml(packets, name, out_dir="mag_models")

if __name__ == "__main__":
    mag_orbit_test()
