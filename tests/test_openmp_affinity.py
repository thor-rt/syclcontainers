"""Check affinity allocation on whole cores and SMT-only allocations. [AI-Codex]"""
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "affinity", Path(__file__).with_name("run_openmp_affinity.py"))
affinity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(affinity)


class AffinityAllocationTests(unittest.TestCase):
    def run_with_topology(self, topology):
        calls = []

        def read_topology(path):
            cpu = int(path.parent.parent.name[3:])
            index = 0 if path.name == "physical_package_id" else 1
            return str(topology[cpu][index])

        with patch.object(affinity.os, "sched_getaffinity", return_value=set(topology)), \
                patch.object(affinity.Path, "read_text", read_topology), \
                patch.object(affinity.subprocess, "run", side_effect=lambda *a, **kw: calls.append((a, kw))), \
                patch("sys.stdout", new_callable=io.StringIO):
            affinity.main()
        return [call for call in calls if call[0][0][0] == "taskset"]

    def test_smt_siblings_still_run_all_kernel_checks(self):
        calls = self.run_with_topology({3: (0, 1), 11: (0, 1)})
        self.assertEqual(len(calls), 4)
        for args, kwargs in calls:
            self.assertEqual(args[0][2], "3,11")
            self.assertEqual(kwargs["env"]["OMP_NUM_THREADS"], "2")
            self.assertEqual(kwargs["env"]["OMP_PLACES"], "threads")
        self.assertEqual([kw["env"]["OMP_PROC_BIND"] for _, kw in calls],
                         ["close", "spread", "close", "spread"])

    def test_distinct_cores_remain_preferred(self):
        calls = self.run_with_topology({0: (0, 0), 2: (0, 2), 8: (0, 0), 10: (0, 2)})
        self.assertEqual(len(calls), 4)
        for args, kwargs in calls:
            self.assertEqual(args[0][2], "2,8")
            self.assertEqual(kwargs["env"]["OMP_PLACES"], "cores")
            self.assertEqual(kwargs["env"]["OMP_NUM_THREADS"], "2")

    def test_one_allowed_cpu_is_still_an_error(self):
        with self.assertRaises(RuntimeError):
            self.run_with_topology({3: (0, 1)})


if __name__ == "__main__":
    unittest.main()
