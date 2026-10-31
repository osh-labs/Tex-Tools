#!/usr/bin/env python3
# reference_vectors.py - reference cases that pin the bartack strength model
# Copyright (C) 2026 Southeast Expedition Medical, LLC, Chris Lee
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Reference vectors for bartack_calc.py.

Each case runs the calculator and stores the unrounded results in reference_vectors.json.
Ports of the model (BartackStudio) are parity-tested against this file, so any change to the
model must regenerate it in the same commit and say why.

    python3 -I bartack_calculator/reference_vectors.py           # check (exit 1 on mismatch)
    python3 -I bartack_calculator/reference_vectors.py --write   # regenerate the JSON
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bartack_calc as bc  # noqa: E402

OUT = Path(__file__).resolve().with_name("reference_vectors.json")
REL_TOL = 1e-12

# name, joint, thread, webbing, L mm, W mm, total stitches, rows, passes, layers, angle, peel, SF, eta
CASES = [
    ("lap_reference",        "lap",  "69",  "1in_mil17337",      25.4, 12.7, 42, 2, 1, 2,   0.0, False, 3.0, None),
    ("loop_reference",       "loop", "69",  "1in_mil17337",      25.4, 12.7, 42, 2, 1, 2,   0.0, False, 3.0, None),
    ("peel",                 "lap",  "138", "1.5in_mil17337",    30.0, 15.0, 60, 2, 1, 2,   0.0, True,  3.0, None),
    ("angle_30",             "lap",  "138", "1in_mil17337",      25.4, 12.7, 42, 2, 1, 2,  30.0, False, 3.0, None),
    ("angle_60",             "lap",  "138", "1in_mil17337",      25.4, 12.7, 42, 2, 1, 2,  60.0, False, 3.0, None),
    ("angle_90",             "lap",  "138", "1in_mil17337",      25.4, 12.7, 42, 2, 1, 2,  90.0, False, 3.0, None),
    ("angle_135_symmetric",  "lap",  "138", "1in_mil17337",      25.4, 12.7, 42, 2, 1, 2, 135.0, False, 3.0, None),
    ("aspect_below_1",       "lap",  "69",  "2in_mil17337",       8.0, 20.0, 30, 2, 1, 2,   0.0, False, 3.0, None),
    ("aspect_above_6",       "lap",  "69",  "1in_mil17337",      40.0,  4.0, 50, 2, 1, 2,   0.0, False, 3.0, None),
    ("no_zigzag",            "lap",  "207", "1in_mil17337",      25.0, 10.0, 40, 2, 0, 2,   0.0, False, 3.0, None),
    ("zigzag_only",          "lap",  "207", "1in_mil17337",      25.0, 10.0, 40, 0, 1, 2,   0.0, False, 3.0, None),
    ("tear_out_governs",     "lap",  "415", "1in_mil17337",       5.0,  3.0, 40, 2, 1, 2,   0.0, False, 3.0, None),
    ("tear_out_capped",      "loop", "415", "1in_aa55301_type3", 30.0, 20.0, 80, 2, 1, 3,   0.0, False, 3.0, None),
    ("webbing_governs",      "loop", "415", "1in_aa55301_type3", 30.0, 20.0, 80, 2, 1, 3,   0.0, False, 3.0, 0.80),
    ("layers_1",             "lap",  "277", "1in_mil17337",      25.4, 12.7, 42, 2, 1, 1,   0.0, False, 2.0, 0.90),
    ("layers_4",             "lap",  "277", "2in_mil17337",      25.4, 25.4, 60, 2, 1, 4,  45.0, True,  5.0, 0.70),
]


def run_case(c):
    (name, joint, thread, webbing, L, W, n, rows, passes, layers, angle, peel, sf, eta) = c
    t = bc.get_thread(thread)
    w = bc.get_webbing(webbing)
    g = bc.TackGeometry(
        joint_type=joint, tack_length_mm=L, tack_width_mm=W, n_straight_rows=rows,
        n_zigzag_passes=passes, total_stitches=n, layer_count=layers,
        webbing_thickness_mm=w.thickness_mm, load_angle_deg=angle,
    )
    r = bc.run_calculator(t, w, g, peel=peel, safety_factor=sf, joint_efficiency=eta)
    return {
        "inputs": {
            "joint": joint, "thread": thread, "webbing": webbing, "tack_length_mm": L,
            "tack_width_mm": W, "total_stitches": n, "straight_rows": rows,
            "zigzag_passes": passes, "layers": layers, "load_angle_deg": angle, "peel": peel,
            "safety_factor": sf, "joint_efficiency": eta,
            "thread_breaking_strength_n": t.breaking_strength_n,
            "webbing_tensile_strength_n": w.tensile_strength_n,
            "webbing_width_mm": w.width_mm,
            "webbing_shear_n_per_mm": w.shear_strength_n_per_mm,
        },
        "expected": {
            "k_sl": bc.k_shear_lag(g.aspect_ratio()),
            "k_angle": bc.k_load_angle(angle),
            "n_straight_stitches": g.total_straight_stitches(),
            "n_zigzag_stitches": g.total_zigzag_stitches(),
            "layers_per_side": g.layers_per_side(),
            "thread_shear_n": r.thread_shear_n,
            "tear_out_uncapped_n": r.tear_out_detail["uncapped_n"],
            "tear_out_n": r.tear_out_n,
            "tear_out_capped": r.tear_out_detail["capped_at_webbing_tensile"],
            "webbing_tensile_n": r.webbing_tensile_n,
            "governing_mode": r.governing_mode,
            "design_strength_n": r.design_strength_n,
            "allowable_load_n": r.allowable_load_n,
            "warning_ids": [wn.split(":", 1)[0] for wn in r.warnings],
        },
    }


def build():
    return {
        "model": "bartack_calc.py (Tex-Tools)",
        "note": "Unrounded results except tear_out_uncapped_n (rounded to 0.01 N by the model's "
                "detail dict). Regenerate with --write whenever the model changes.",
        "cases": {c[0]: run_case(c) for c in CASES},
    }


def _same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-9)
    return a == b


def main():
    data = build()
    if "--write" in sys.argv:
        OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {len(data['cases'])} cases to {OUT.name}")
        return 0
    stored = json.loads(OUT.read_text(encoding="utf-8"))
    bad = []
    for name, case in data["cases"].items():
        old = stored["cases"].get(name)
        if old is None:
            bad.append(f"{name}: missing from {OUT.name}")
            continue
        for k, v in case["expected"].items():
            if not _same(v, old["expected"].get(k)):
                bad.append(f"{name}.{k}: stored {old['expected'].get(k)!r}, now {v!r}")
    for line in bad:
        print(line)
    print("OK" if not bad else f"{len(bad)} mismatches")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
