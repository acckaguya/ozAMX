import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from diagnose_fp64_alternative import (
    bf16_bits_from_slices, decompose, round_to_bf16_f64, scalar_self_test,
)


class FP64AlternativeScalarTests(unittest.TestCase):
    def test_scalar_self_test(self):
        scalar_self_test()

    def test_ties_to_even_is_direct_from_binary64(self):
        got = round_to_bf16_f64([1.0 + 2.0**-8, 1.0 + 3.0 * 2.0**-8])
        self.assertEqual(got.tolist(), [1.0, 1.0 + 2.0**-6])

    def test_all_methods_emit_six_exact_bf16_slices_for_scalar(self):
        for method in ("paper_literal_rho45", "direct_bf16_residual", "diagnostic_rho44"):
            parts, terminal, layers = decompose([0.7], method)
            self.assertEqual(len(parts), 6)
            self.assertTrue(all(row["component_is_exact_bf16"] for row in layers))
            self.assertTrue(all(float(x[0]) == x[0] for x in parts))
            self.assertTrue(abs(float(terminal[0])) < 1e-12)

    def test_raw_bf16_little_endian_words(self):
        values = [np.array([1.0, -2.0, 0.0, -0.0], dtype="float64")]
        got = bf16_bits_from_slices(values)
        self.assertEqual(got.dtype.str, "<u2")
        self.assertEqual(got[0].tolist(), [0x3F80, 0xC000, 0x0000, 0x8000])


if __name__ == "__main__":
    unittest.main()
