"""Publish a Cesium page demonstrating multiple arbitrary CZML vectors."""

import numpy as np
from sgp4.api import Satrec

from czml import R_EARTH, build_czml
from output import publish_czml

EX_TLE1 = "1 25544U 98067A   26305.53114906  .00006056  00000+0  11739-3 0  9995"
EX_TLE2 = "2 25544  51.6332 340.4448 0007086 335.8887  24.1768 15.49140542593046"
PAGE_NAME = "CZML Arbitrary Vectors"


def build_test_packets(n_steps=180):
    """Build an example orbit with vectors having different origins."""
    satrec = Satrec.twoline2rv(EX_TLE1, EX_TLE2)
    period_min = 2 * np.pi / satrec.no_kozai
    t_min = np.linspace(0.0, period_min, n_steps)
    jd = np.full(n_steps, satrec.jdsatepoch)
    fr = satrec.jdsatepochF + t_min / 1440.0
    errors, sat_xyz, _ = satrec.sgp4_array(jd, fr)
    if np.any(errors):
        raise RuntimeError(f"SGP4 failed with error code {errors}")

    phase = np.linspace(0.0, 2 * np.pi, n_steps)
    satellite_vector = np.column_stack((
        900.0 * np.cos(phase),
        900.0 * np.sin(phase),
        500.0 * np.sin(2 * phase),
    ))

    earth_directions = np.column_stack((
        np.cos(phase),
        np.sin(phase),
        np.full(n_steps, 0.35),
    ))
    earth_directions /= np.linalg.norm(earth_directions, axis=1, keepdims=True)

    offset_vector = np.column_stack((
        np.full(n_steps, 300.0),
        600.0 * np.cos(phase),
        600.0 * np.sin(phase),
    ))
    vectors = [
        (satellite_vector, sat_xyz),
        (earth_directions * (1.5 * R_EARTH), np.zeros(3)),
        (offset_vector, np.array([R_EARTH, 0.0, 0.0])),
    ]

    return build_czml(
        t_min, jd, fr, sat_xyz, vectors,
        name=PAGE_NAME,
        sat_name="ISS",
    )


def main():
    packets = build_test_packets()
    publish_czml(packets, PAGE_NAME, out_dir="vector_tests")


if __name__ == "__main__":
    main()