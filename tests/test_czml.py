import unittest

from czml import R_EARTH, build_czml


class BuildCzmlTests(unittest.TestCase):
    def setUp(self):
        self.t_min = [0.0, 1.0]
        self.jd = [2451545.0, 2451545.0]
        self.fr = [0.0, 1.0 / 1440.0]
        self.sat_xyz = [
            [R_EARTH + 400.0, 0.0, 0.0],
            [0.0, R_EARTH + 400.0, 0.0],
        ]

    def test_draws_each_vector_from_its_start(self):
        vectors = [
            ([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]),
            (
                [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
                [[0.0, 0.0, 1.0], [0.0, 0.0, 2.0]],
            ),
        ]

        packets = build_czml(
            self.t_min, self.jd, self.fr, self.sat_xyz, vectors,
            show_ucla=False,
        )
        packets_by_id = {packet["id"]: packet for packet in packets}

        self.assertIn("satellite", packets_by_id)
        self.assertNotIn("comms", packets_by_id)
        self.assertEqual(
            packets_by_id["vector_0"]["polyline"]["positions"]["references"],
            ["vector_0_start#position", "vector_0_end#position"],
        )
        self.assertEqual(
            packets_by_id["vector_0_end"]["position"]["cartesian"],
            [0.0, 5000.0, 7000.0, 9000.0,
             60.0, 5000.0, 7000.0, 9000.0],
        )
        self.assertEqual(
            packets_by_id["vector_1_end"]["position"]["cartesian"],
            [0.0, 1000.0, 0.0, 1000.0,
             60.0, 0.0, 2000.0, 2000.0],
        )

    def test_rejects_vector_data_with_invalid_shape(self):
        with self.assertRaises(ValueError):
            build_czml(
                self.t_min, self.jd, self.fr, self.sat_xyz,
                [([1.0, 2.0], [0.0, 0.0, 0.0])],
            )


if __name__ == "__main__":
    unittest.main()
