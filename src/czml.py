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

def _position_series(values, sample_count, label):
    """Return one XYZ value per sample, broadcasting a single XYZ triple."""
    values = np.asarray(values, dtype=float)
    if values.shape == (3,):
        return np.repeat(values[None, :], sample_count, axis=0)
    if values.shape != (sample_count, 3):
        raise ValueError(
            f"{label} must have shape (3,) or ({sample_count}, 3); "
            f"got {values.shape}"
        )
    return values

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
def build_czml(t_min, jd, fr, sat_xyz, vectors, R=R_EARTH,
               name="Model", sat_name="ISS", show_ucla=True):
    """Build CZML for a satellite orbit and vector displacements.

    `t_min`, `jd`, and `fr` are length-N time arrays. `sat_xyz` contains N
    satellite positions in km. Each item in `vectors` is
    `(vector_xyz, start_xyz)`, where either value is one XYZ triple or an
    N-by-3 series, in km. The vector endpoint is `start_xyz + vector_xyz`.
    """
    N = len(t_min)
    t_sec = np.asarray(t_min, dtype=float) * 60.0
    sat_xyz = _position_series(sat_xyz, N, "sat_xyz")

    iso_times = [_iso(j, f) for j, f in zip(jd, fr)]
    epoch, end = iso_times[0], iso_times[-1]
    avail = f"{epoch}/{end}"
    duration = float(t_sec[-1])

    sat_radius = np.linalg.norm(sat_xyz, axis=1)
    zenith = sat_xyz / sat_radius[:, None]
    altitude = sat_radius - R
    nadir_foot = zenith * R
    descriptions = [f"<p>altitude {a:.1f} km</p>" for a in altitude]

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
                "leadTime": duration,
                "trailTime": duration,
                "width": 2,
                "resolution": 60,
                "material": {"solidColor": {"color": {"rgba": ORBIT_GREY}}},
            },
        },
        {
            "id": "nadir_foot",
            "name": "nadir foot",
            "availability": avail,
            "position": _sampled_position(epoch, t_sec, nadir_foot),
        },
        _line("altitude", "altitude", avail, WHITE, 3,
              {"references": ["nadir_foot#position", "satellite#position"]},
              dash=True),
    ]

    for i, vector_spec in enumerate(vectors):
        if len(vector_spec) != 2:
            raise ValueError(
                f"vectors[{i}] must be a (vector_xyz, start_xyz) pair"
            )
        vector_xyz, start_xyz = vector_spec
        vector_xyz = _position_series(vector_xyz, N, f"vectors[{i}].vector_xyz")
        start_xyz = _position_series(start_xyz, N, f"vectors[{i}].start_xyz")
        end_xyz = start_xyz + vector_xyz
        start_id = f"vector_{i}_start"
        end_id = f"vector_{i}_end"
        vector_name = f"Vector {i + 1}"
        color = [GOLD, RED, LIME, CRIMSON][i % 4]

        packets.extend([
            {
                "id": start_id,
                "name": f"{vector_name} start",
                "availability": avail,
                "position": _sampled_position(epoch, t_sec, start_xyz),
            },
            {
                "id": end_id,
                "name": f"{vector_name} end",
                "availability": avail,
                "position": _sampled_position(epoch, t_sec, end_xyz),
            },
            _line(
                f"vector_{i}", vector_name, avail, color, 10,
                {"references": [f"{start_id}#position", f"{end_id}#position"]},
                arrow=True,
            ),
        ])

    if show_ucla:
        packets.append({
            "id": "comms",
            "name": "UCLA",
            "position": {
                "cartographicDegrees": [-118.4427, 34.0722, 0.0]
            },
            "point": {
                "color": {"rgba": [255, 0, 0, 255]},
                "pixelSize": 10,
                "outlineColor": {"rgba": WHITE},
                "outlineWidth": 2,
            },
        })

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
