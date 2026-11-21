"""Publish a Cesium page demonstrating multiple arbitrary CZML vectors."""

import numpy as np
from sgp4.api import Satrec

from czml import R_EARTH, build_czml
from output import publish_czml

EX_TLE1 = "1 25544U 98067A   26305.53114906  .00006056  00000+0  11739-3 0  9995"
EX_TLE2 = "2 25544  51.6332 340.4448 0007086 335.8887  24.1768 15.49140542593046"
PAGE_NAME = "CZML Arbitrary Vectors"


def build_test_packets(n_steps=180):
    """Build free-standing vectors plus vectors sourced from scene objects."""
    satrec = Satrec.twoline2rv(EX_TLE1, EX_TLE2)
    period_min = 2 * np.pi / satrec.no_kozai
    t_min = np.linspace(0.0, period_min, n_steps)
    jd = np.full(n_steps, satrec.jdsatepoch)
    fr = satrec.jdsatepochF + t_min / 1440.0
    errors, sat_xyz, _ = satrec.sgp4_array(jd, fr)
    if np.any(errors):
        raise RuntimeError(f"SGP4 failed with error code {errors}")

    displacements = [
        [600.0, 0.0, 0.0],
        [0.0, 800.0, 0.0],
        [0.0, 0.0, 1100.0],
        [-1350.0, 0.0, 0.0],
        [0.0, -1600.0, 0.0],
        [0.0, 0.0, 1900.0],
        [2200.0, 0.0, 0.0],
        [0.0, 2600.0, 0.0],
        [0.0, 0.0, -3000.0],
        [-3400.0, 0.0, 0.0],
    ]
    vectors = []
    for i, displacement in enumerate(displacements):
        start = np.array([
            30000.0 + 7000.0 * i,
            25000.0 + 8000.0 * (i % 2),
            20000.0 + 6000.0 * (i % 3),
        ])
        vectors.append((np.asarray(displacement), start))

    earth_directions = np.array([
        [1.0, 0.0, 0.0],
        [1.0, 0.15, 0.1],
    ])
    earth_directions /= np.linalg.norm(earth_directions, axis=1, keepdims=True)
    earth_lengths = [1200.0, 1800.0]
    for direction, length in zip(earth_directions, earth_lengths):
        vectors.append((direction * length, direction * R_EARTH))

    sun_origin = np.array([85000.0, 45000.0, 35000.0])
    vectors.append((np.array([0.0, 0.0, 1600.0]), sun_origin))

    satellite_direction = sat_xyz / np.linalg.norm(sat_xyz, axis=1, keepdims=True)
    vectors.append((satellite_direction * 1400.0, sat_xyz))

    packets = build_czml(
        t_min, jd, fr, sat_xyz, vectors,
        name=PAGE_NAME,
        sat_name="ISS",
    )
    labels = {
        "vector_10": "Earth surface vector 1",
        "vector_11": "Earth surface vector 2",
        "vector_12": "Illustrative Sun vector",
        "vector_13": "Satellite vector",
    }
    for packet in packets:
        if packet.get("id") in labels:
            packet["name"] = labels[packet["id"]]

    packets.append({
        "id": "illustrative_sun",
        "name": "Illustrative Sun (not to scale)",
        "position": {
            "referenceFrame": "INERTIAL",
            "cartesian": (sun_origin * 1000.0).tolist(),
        },
        "point": {
            "pixelSize": 12,
            "color": {"rgba": [255, 215, 0, 255]},
            "outlineColor": {"rgba": [255, 255, 255, 255]},
            "outlineWidth": 2,
        },
        "label": {
            "text": "Illustrative Sun (not to scale)",
            "font": "bold 14px sans-serif",
            "fillColor": {"rgba": [255, 215, 0, 255]},
        },
    })
    return packets


def main():
    packets = build_test_packets()
    publish_czml(packets, PAGE_NAME, out_dir="vector_tests")


if __name__ == "__main__":
    main()