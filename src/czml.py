"""
CesiumJS Builder Helper Code

This is mostly helpful for per-orbit rendering
Note that local builds will not have access to ion even with
the correct environment variable
"""

from datetime import datetime, timedelta, timezone

import numpy as np

R_EARTH = 6371.0  # km
KM = 1000.0       # CZML wants metres

J2000_JD = 2451545.0
J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# RGBA colours (CZML wants 0-255 ints)
GOLD = [255, 215, 0, 255]
RED = [255, 0, 0, 255]
LIME = [50, 205, 50, 255]
WHITE = [255, 255, 255, 255]
CRIMSON = [220, 20, 60, 255]
ORBIT_GREY = [220, 220, 220, 153]

# ----------------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------------
def _geometry_series(sat_xyz, sun_xyz, R):
    """Per-step unit sat->Sun vector, zenith, altitude (km), sun/zenith angle (deg)."""
    sat_to_sun = sun_xyz - sat_xyz
    u = sat_to_sun / np.linalg.norm(sat_to_sun, axis=1, keepdims=True)
    r_sat = np.linalg.norm(sat_xyz, axis=1)
    zenith = sat_xyz / r_sat[:, None]
    angle = np.degrees(np.arccos(np.clip(np.sum(u * zenith, axis=1), -1, 1)))
    return u, zenith, r_sat - R, angle


# ----------------------------------------------------------------------------
# CZML helpers
# ----------------------------------------------------------------------------
def _iso(jd, fr):
    """Julian date (jd + fr) -> ISO 8601 UTC string with ms precision."""
    dt = J2000 + timedelta(days=(float(jd) - J2000_JD) + float(fr))
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _sampled_position(epoch, t_sec, xyz_km):
    """Time-tagged inertial position property: [t, x, y, z, ...] in metres."""
    flat = []
    for t, p in zip(t_sec, np.asarray(xyz_km) * KM):
        flat += [float(t), float(p[0]), float(p[1]), float(p[2])]
    return {
        "epoch": epoch,
        "referenceFrame": "INERTIAL",
        "interpolationAlgorithm": "LAGRANGE",
        "interpolationDegree": 5,
        "cartesian": flat,
    }


def _line(id_, name, availability, color, width, positions,
          arrow=False, dash=False):
    """Polyline entity. `positions` is {"references": [...]} or {"cartesian": [...]}."""
    if arrow:
        material = {"polylineArrow": {"color": {"rgba": color}}}
    elif dash:
        material = {"polylineDash": {"color": {"rgba": color}, "dashLength": 16}}
    else:
        material = {"solidColor": {"color": {"rgba": color}}}
    return {
        "id": id_,
        "name": name,
        "availability": availability,
        "polyline": {
            "positions": positions,
            "width": width,
            "material": material,
            "arcType": "NONE",  # straight 3D lines, not geodesics hugging the globe
        },
    }


def _description_intervals(iso_times, html_strings):
    """Step-wise (per sample) description so the info box updates with time."""
    out = []
    for i in range(len(iso_times) - 1):
        out.append({"interval": f"{iso_times[i]}/{iso_times[i + 1]}",
                    "string": html_strings[i]})
    return out


# ----------------------------------------------------------------------------
# CZML builder
# ----------------------------------------------------------------------------
def build_czml(t_min, jd, fr, sat_xyz, sun_xyz, R=R_EARTH,
               name="Model", sat_name="ISS", show_ucla = True):
    """Return a CZML document (list of packets) for the orbit + sun geometry."""
    N = len(t_min)
    L = R  # length of the sat->Sun arrow, km (same as the plotly version)
    t_sec = np.asarray(t_min) * 60.0

    iso_times = [_iso(j, f) for j, f in zip(jd, fr)]
    epoch, end = iso_times[0], iso_times[-1]
    avail = f"{epoch}/{end}"
    duration = float(t_sec[-1])

    u, zenith, alt, angle = _geometry_series(sat_xyz, sun_xyz, R)
    s_hat = sun_xyz / np.linalg.norm(sun_xyz, axis=1, keepdims=True)

    # Derived points (km, inertial) used as polyline endpoints
    sun_arrow_tip = sat_xyz + u * L            # sat -> Sun arrow end
    nadir_foot = zenith * R                    # altitude stem foot on the sphere
    earth_sun_tip = s_hat * 2 * R              # Earth -> Sun direction end

    descriptions = [
        f"<p>altitude {a:.1f} km<br>angle between sat&rarr;Sun and local zenith: "
        f"{g:.1f}&deg;</p>"
        for a, g in zip(alt, angle)
    ]

    packets = [
        {
            "id": "document",
            "name": name,
            "version": "1.0",
            "clock": {
                "interval": avail,
                "currentTime": epoch,
                "multiplier": 60,
                "range": "LOOP_STOP",
                "step": "SYSTEM_CLOCK_MULTIPLIER",
            },
        },
        # --- satellite: marker + full-orbit path + live info box ---
        {
            "id": "satellite",
            "name": sat_name,
            "availability": avail,
            "description": _description_intervals(iso_times, descriptions),
            "position": _sampled_position(epoch, t_sec, sat_xyz),
            "point": {
                "pixelSize": 10,
                "color": {"rgba": CRIMSON},
                "outlineColor": {"rgba": WHITE},
                "outlineWidth": 1,
            },
            "path": {
                "show": True,
                "leadTime": duration,   # show the whole orbit at all times
                "trailTime": duration,
                "width": 2,
                "resolution": 60,
                "material": {"solidColor": {"color": {"rgba": ORBIT_GREY}}},
            },
        },
        # --- invisible helper entities (position only) used as line endpoints ---
        {"id": "sun_arrow_tip", "name": "sat → Sun tip", "availability": avail,
         "position": _sampled_position(epoch, t_sec, sun_arrow_tip)},
        {"id": "nadir_foot", "name": "nadir foot", "availability": avail,
         "position": _sampled_position(epoch, t_sec, nadir_foot)},
        {"id": "earth_sun_tip", "name": "Earth → Sun tip", "availability": avail,
         "position": _sampled_position(epoch, t_sec, earth_sun_tip)},
        {"id": "earth_center", "name": "Earth centre", "availability": avail,
         "position": {"referenceFrame": "INERTIAL", "cartesian": [0.0, 0.0, 0.0]}},
        # --- dynamic lines, built from entity position references ---
        _line("altitude", "altitude", avail, WHITE, 3,
              {"references": ["nadir_foot#position", "satellite#position"]},
              dash=True),
        _line("sat_to_sun", "sat → Sun", avail, GOLD, 10,
              {"references": ["satellite#position", "sun_arrow_tip#position"]},
              arrow=True),
        _line("earth_to_sun", "Earth → Sun (direction)", avail, RED, 8,
              {"references": ["earth_center#position", "earth_sun_tip#position"]},
              arrow=True),
    ]

    # if show_ucla:
    packets.append({
        "id": "comms",
        "name": "UCLA",
        "position": {
            "cartographicDegrees": [
                -118.4427, 34.0722, 0.0
            ]
        },
        "point": {
            "color": {
                "rgba": [255, 0, 0, 255]
            },
            "pixelSize": 10,
            "outlineColor": {
                "rgba": [255, 255, 255, 255]
            },
            "outlineWidth": 2
        }
    })

    # --- static North vector in the Earth-fixed frame: +z from the pole outward ---
    north_len = 0.7 * R
    packets.append(_line(
        "north", "North (+z)", avail, LIME, 10,
        {"cartesian": [0.0, 0.0, R * KM, 0.0, 0.0, (R + north_len) * KM]},
        arrow=True))
    packets.append({
        "id": "north_label",
        "name": "N",
        "availability": avail,
        "position": {"cartesian": [0.0, 0.0, (R + north_len * 1.25) * KM]},
        "label": {
            "text": "N",
            "font": "bold 20px sans-serif",
            "style": "FILL",
            "fillColor": {"rgba": LIME},
            "horizontalOrigin": "CENTER",
        },
    })

    return packets
