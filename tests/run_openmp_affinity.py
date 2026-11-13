#!/usr/bin/env python3
"""Check real CPU kernels with binding enabled and one OpenMP runtime. [AI-Codex]"""
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    # Pick one hardware thread per physical core from the actual allocation.
    # Prefer CPUs other than zero to catch hard-coded placement assumptions.
    available = sorted(os.sched_getaffinity(0), key=lambda value: (value == 0, value))
    cores = {}
    for cpu in available:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        core = ((topology / "physical_package_id").read_text().strip(),
                (topology / "core_id").read_text().strip())
        cores.setdefault(core, cpu)
    cpus = sorted(list(cores.values())[:4])
    places = "cores"
    if len(cpus) < 2:
        # Small CI runners may expose only SMT siblings. Distinct hardware
        # threads still detect a kernel team confined to one logical CPU.
        cpus = sorted(available[:4])
        places = "threads"
    if len(cpus) < 2:
        raise RuntimeError(f"OpenMP affinity regression requires at least two allowed CPUs; "
                           f"got {len(available)}")
    allocation = ",".join(map(str, cpus))
    print(f"OpenMP affinity test allocation: {allocation}; "
          f"{len(cores)} physical core(s) available; OMP_PLACES={places}", flush=True)
    source = Path(__file__).with_name("openmp_affinity.cpp")
    compiler = os.environ.get("CXX", "acpp")
    env = dict(os.environ, ACPP_VISIBILITY_MASK="omp", OMP_NUM_THREADS=str(len(cpus)),
               OMP_PLACES=places, OMP_DYNAMIC="false")
    # Keep this regression independent of an invoking shell's affinity overrides.
    for variable in ("KMP_AFFINITY", "GOMP_CPU_AFFINITY", "KMP_HW_SUBSET"):
        env.pop(variable, None)
    with tempfile.TemporaryDirectory(prefix="openmp-affinity-") as directory:
        env["ACPP_APPDB_DIR"] = directory + "/cache"
        for target in ("generic", "omp"):
            executable = str(Path(directory) / target)
            subprocess.run([compiler, f"--acpp-targets={target}", "-O2", "-fopenmp",
                            "-pthread", str(source), "-ldl", "-o", executable],
                           check=True, env=env)
            for binding in ("close", "spread"):
                print(f"Testing {target}, OMP_PROC_BIND={binding}", flush=True)
                subprocess.run(["taskset", "--cpu-list", allocation, executable, allocation],
                               check=True, env=dict(env, OMP_PROC_BIND=binding), timeout=120)


if __name__ == "__main__":
    main()
