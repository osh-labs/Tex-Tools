#!/usr/bin/env python3
"""
bartack.py — Bartack Design Strength Calculator
================================================
Calculates the design strength of a bartack on webbing-on-webbing joints.
Models two failure paths: thread shear and tear-out. Returns governing (minimum) strength.

SCOPE: Webbing-on-webbing joints only. Not valid for webbing-to-fabric joints.
All results are design estimates. Validate with destructive testing before use.

Usage (interactive):
    python bartack.py

Usage (argparse / scriptable):
    python bartack.py \\
        --joint lap \\
        --thread 69 \\
        --webbing 1in_nylon_flat \\
        --tack-length "1.0 in" \\
        --tack-width "0.5 in" \\
        --straight-rows 4 \\
        --zigzag-passes 2 \\
        --stitch-pitch "2.0 mm" \\
        --layers 2 \\
        --load-angle 0 \\
        --peel \\
        --safety-factor 3.0 \\
        --output human

    --output human    : formatted report to stdout (default)
    --output json     : JSON to stdout for piping
    --list-threads    : print available thread keys and exit
    --list-webbings   : print available webbing keys and exit
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional


# =============================================================================
# UNITS
# =============================================================================

def to_mm(value: float, unit: str) -> float:
    """Convert a length value to millimeters."""
    unit = unit.strip().lower()
    conversions = {"mm": 1.0, "cm": 10.0, "in": 25.4, "ft": 304.8}
    if unit not in conversions:
        raise ValueError(f"Unknown length unit '{unit}'. Supported: {list(conversions)}")
    return value * conversions[unit]


def to_newtons(value: float, unit: str) -> float:
    """Convert a force value to Newtons."""
    unit = unit.strip().lower()
    conversions = {"n": 1.0, "kn": 1000.0, "lbf": 4.44822, "kip": 4448.22}
    if unit not in conversions:
        raise ValueError(f"Unknown force unit '{unit}'. Supported: {list(conversions)}")
    return value * conversions[unit]


def to_n_per_mm(value: float, unit: str) -> float:
    """Convert a linear force density to N/mm."""
    unit = unit.strip().lower()
    if unit == "n/mm":
        return value
    elif unit == "lbf/in":
        return value * 4.44822 / 25.4
    else:
        raise ValueError(f"Unknown linear density unit '{unit}'. Supported: n/mm, lbf/in")


def from_mm(value_mm: float, target_unit: str) -> float:
    """Convert mm to target unit."""
    target_unit = target_unit.strip().lower()
    conversions = {"mm": 1.0, "cm": 0.1, "in": 1.0 / 25.4, "ft": 1.0 / 304.8}
    if target_unit not in conversions:
        raise ValueError(f"Unknown length unit '{target_unit}'")
    return value_mm * conversions[target_unit]


def from_newtons(value_n: float, target_unit: str) -> float:
    """Convert Newtons to target unit."""
    target_unit = target_unit.strip().lower()
    conversions = {"n": 1.0, "kn": 0.001, "lbf": 1.0 / 4.44822, "kip": 1.0 / 4448.22}
    if target_unit not in conversions:
        raise ValueError(f"Unknown force unit '{target_unit}'")
    return value_n * conversions[target_unit]


def parse_value_unit(s: str, kind: str) -> float:
    """
    Parse a string like '1.0 in' or '25.4mm' into SI units.
    kind: 'length' -> mm, 'force' -> N, 'linear_density' -> N/mm
    """
    s = s.strip()
    # Split numeric part from unit part
    i = 0
    while i < len(s) and (s[i].isdigit() or s[i] in ".+-eE"):
        i += 1
    num_str = s[:i].strip()
    unit_str = s[i:].strip()
    if not num_str:
        raise ValueError(f"Could not parse value from '{s}'")
    value = float(num_str)
    if kind == "length":
        return to_mm(value, unit_str if unit_str else "mm")
    elif kind == "force":
        return to_newtons(value, unit_str if unit_str else "n")
    elif kind == "linear_density":
        return to_n_per_mm(value, unit_str if unit_str else "n/mm")
    else:
        raise ValueError(f"Unknown kind '{kind}'")


# =============================================================================
# MATERIALS — THREAD
# =============================================================================

@dataclass
class Thread:
    name: str
    size_designation: str
    breaking_strength_n: float   # Tensile breaking strength, N
    diameter_mm: float           # Nominal thread diameter, mm
    elongation_at_break: float   # Fraction (0.20 = 20%)
    elongation_assumed: bool     # True if elongation is a default assumption


# Bonded nylon thread lookup table.
# Breaking strength values from Coats Industrial thread specs (tex-based bonded nylon).
# Diameter values are nominal estimates; verify against actual spool specs.
# Elongation at break: 0.20 default where not published (assumption A7).
_THREAD_TABLE = {
    "69": Thread(
        name="Bonded Nylon #69",
        size_designation="69",
        breaking_strength_n=53.4,    # ~12 lbf
        diameter_mm=0.40,
        elongation_at_break=0.20,
        elongation_assumed=True,
    ),
    "138": Thread(
        name="Bonded Nylon #138",
        size_designation="138",
        breaking_strength_n=106.8,   # ~24 lbf
        diameter_mm=0.55,
        elongation_at_break=0.20,
        elongation_assumed=True,
    ),
    "207": Thread(
        name="Bonded Nylon #207",
        size_designation="207",
        breaking_strength_n=160.1,   # ~36 lbf
        diameter_mm=0.67,
        elongation_at_break=0.20,
        elongation_assumed=True,
    ),
    "277": Thread(
        name="Bonded Nylon #277",
        size_designation="277",
        breaking_strength_n=213.5,   # ~48 lbf
        diameter_mm=0.78,
        elongation_at_break=0.20,
        elongation_assumed=True,
    ),
    "346": Thread(
        name="Bonded Nylon #346",
        size_designation="346",
        breaking_strength_n=266.9,   # ~60 lbf
        diameter_mm=0.87,
        elongation_at_break=0.20,
        elongation_assumed=True,
    ),
    "415": Thread(
        name="Bonded Nylon #415",
        size_designation="415",
        breaking_strength_n=320.3,   # ~72 lbf
        diameter_mm=0.95,
        elongation_at_break=0.20,
        elongation_assumed=True,
    ),
}


def get_thread(size_designation: str) -> Thread:
    key = str(size_designation).strip()
    if key not in _THREAD_TABLE:
        raise ValueError(
            f"Unknown thread size '{key}'. Available: {list(_THREAD_TABLE)}"
        )
    return _THREAD_TABLE[key]


def list_available_threads() -> list:
    return [
        f"{k:>6}  {v.name:<30}  break: {v.breaking_strength_n:>7.1f} N "
        f"({from_newtons(v.breaking_strength_n, 'lbf'):>5.1f} lbf)  "
        f"dia: {v.diameter_mm:.2f} mm"
        for k, v in _THREAD_TABLE.items()
    ]


# =============================================================================
# MATERIALS — WEBBING
# =============================================================================

@dataclass
class Webbing:
    name: str
    material: str           # nylon | polyester | dyneema | polypro | tubular_nylon
    width_mm: float
    tensile_strength_n: float
    shear_strength_n_per_mm: float
    thickness_mm: float
    construction: str       # flat | tubular
    shear_derived: bool     # True if shear strength was derived via von Mises (A1)


def _make_webbing(name, material, width_mm, tensile_n, thickness_mm, construction,
                  shear_n_per_mm=None):
    """Helper: derive shear strength via von Mises if not provided (assumption A1)."""
    if shear_n_per_mm is None:
        # A1: shear_strength = (tensile / width) * 0.577  (von Mises criterion)
        shear_n_per_mm = (tensile_n / width_mm) * 0.577
        shear_derived = True
    else:
        shear_derived = False
    return Webbing(
        name=name,
        material=material,
        width_mm=width_mm,
        tensile_strength_n=tensile_n,
        shear_strength_n_per_mm=shear_n_per_mm,
        thickness_mm=thickness_mm,
        construction=construction,
        shear_derived=shear_derived,
    )


# Webbing lookup table.
# Tensile strength values are nominal mil-spec / commercial minimums.
# Thickness values are nominal estimates; verify against actual material.
# All shear strengths are von Mises derived (A1) unless noted.
_WEBBING_TABLE = {
    "1in_nylon_flat": _make_webbing(
        "1-inch Nylon Flat Webbing (MIL-W-4088)",
        "nylon", 25.4, 13344.7, 1.5, "flat"        # 3,000 lbf min
    ),
    "1.5in_nylon_flat": _make_webbing(
        "1.5-inch Nylon Flat Webbing",
        "nylon", 38.1, 20017.0, 1.8, "flat"         # 4,500 lbf min
    ),
    "2in_nylon_flat": _make_webbing(
        "2-inch Nylon Flat Webbing (MIL-W-4088)",
        "nylon", 50.8, 26689.3, 2.2, "flat"         # 6,000 lbf min
    ),
    "1in_polyester_flat": _make_webbing(
        "1-inch Polyester Flat Webbing",
        "polyester", 25.4, 13344.7, 1.5, "flat"     # 3,000 lbf min
    ),
    "1in_tubular_nylon": _make_webbing(
        "1-inch Tubular Nylon Webbing",
        "tubular_nylon", 25.4, 11120.6, 3.2, "tubular"  # 2,500 lbf min
    ),
    "1in_dyneema_flat": _make_webbing(
        "1-inch Dyneema/Spectra Flat Webbing",
        "dyneema", 25.4, 22241.1, 1.0, "flat"       # 5,000 lbf min
    ),
    "1in_polypro_flat": _make_webbing(
        "1-inch Polypropylene Flat Webbing",
        "polypro", 25.4, 6672.3, 1.6, "flat"        # 1,500 lbf min
    ),
}


def get_webbing(key: str) -> Webbing:
    key = key.strip()
    if key not in _WEBBING_TABLE:
        raise ValueError(
            f"Unknown webbing '{key}'. Available: {list(_WEBBING_TABLE)}"
        )
    return _WEBBING_TABLE[key]


def list_available_webbings() -> list:
    lines = []
    for k, v in _WEBBING_TABLE.items():
        shear_note = "[derived]" if v.shear_derived else "[measured]"
        lines.append(
            f"{k:<22}  {v.name:<45}  "
            f"tensile: {v.tensile_strength_n:>8.0f} N "
            f"({from_newtons(v.tensile_strength_n, 'lbf'):>6.0f} lbf)  "
            f"shear: {shear_note}"
        )
    return lines


# =============================================================================
# GEOMETRY
# =============================================================================

@dataclass
class TackGeometry:
    joint_type: str          # "lap" | "loop"
    tack_length_mm: float    # Long axis, parallel to load direction
    tack_width_mm: float     # Short axis, across webbing width
    n_straight_rows: int     # Count of straight stitch rows
    n_zigzag_passes: int     # Count of zigzag passes
    stitch_pitch_mm: float   # Center-to-center stitch spacing, mm
    layer_count: int         # Total webbing layers through tack
    webbing_thickness_mm: float  # Per-layer thickness from webbing spec
    load_angle_deg: float    # Load direction re: tack long axis (0 = longitudinal)

    def aspect_ratio(self) -> float:
        return self.tack_length_mm / self.tack_width_mm

    def total_thickness_mm(self) -> float:
        return self.layer_count * self.webbing_thickness_mm

    def effective_shear_area_mm2(self) -> float:
        return self.tack_length_mm * self.tack_width_mm

    def perimeter_mm(self) -> float:
        return 2.0 * (self.tack_length_mm + self.tack_width_mm)

    def stitches_per_row(self) -> int:
        """Stitch count per straight row, derived from length and pitch."""
        return max(1, int(self.tack_length_mm / self.stitch_pitch_mm))

    def total_straight_stitches(self) -> int:
        return self.n_straight_rows * self.stitches_per_row()

    def total_zigzag_stitches(self) -> int:
        # Zigzag pass covers the same length; each stitch spans pitch distance
        return self.n_zigzag_passes * self.stitches_per_row()

    def total_stitch_count(self) -> int:
        return self.total_straight_stitches() + self.total_zigzag_stitches()


# =============================================================================
# CORRECTIONS
# =============================================================================

def k_shear_lag(aspect_ratio: float) -> float:
    """
    Shear lag correction factor K_sl. (Assumption A2)

    Models non-uniform load sharing among stitches along the load axis.
    End stitches carry disproportionate load; the full stitch count never
    contributes simultaneously. Analogous to end-fastener overload in
    riveted lap joints.

    Banding by aspect ratio reflects geometric stress concentration at tack
    corners. Higher aspect ratio = more linear load path = reduced corner
    stress concentration = modestly improved effective stitch engagement.

    NOTE: K_sl models load distribution *within* the tack footprint only.
    The fraction of total webbing load intercepted by the tack is determined
    separately by tack width vs. webbing width. This model assumes tack width
    approximates webbing width (ideal condition). Results are less reliable
    when tack width is substantially less than webbing width.

    Values are conservative estimates. Flag for empirical calibration.
    """
    if aspect_ratio < 1.0:
        # Short, wide tack: higher corner stress concentration, poorer load sharing
        lo, hi, k_lo, k_hi = 0.0, 1.0, 0.60, 0.65
    elif aspect_ratio <= 3.0:
        lo, hi, k_lo, k_hi = 1.0, 3.0, 0.65, 0.75
    else:
        # Long, narrow tack: more linear load path, better stress distribution
        # Capped — adding more length beyond this does not continue to improve sharing
        lo, hi, k_lo, k_hi = 3.0, 6.0, 0.75, 0.85
        aspect_ratio = min(aspect_ratio, 6.0)

    t = (aspect_ratio - lo) / (hi - lo)
    return k_lo + t * (k_hi - k_lo)


def k_load_angle(angle_deg: float) -> float:
    """
    Load angle correction factor K_angle. (Assumption A3)

    Models degradation in effective thread contribution as load direction
    deviates from the tack long axis. Linear interpolation between:
        0 deg  -> 1.00 (full longitudinal shear, optimal)
       45 deg  -> 0.75
       90 deg  -> 0.60 (transverse load, significant strength reduction)

    Values are engineering estimates. Validate with off-axis pull tests.
    """
    angle = abs(angle_deg) % 180.0
    if angle > 90.0:
        angle = 180.0 - angle  # Symmetric about 90 deg

    if angle <= 45.0:
        t = angle / 45.0
        return 1.00 + t * (0.75 - 1.00)
    else:
        t = (angle - 45.0) / 45.0
        return 0.75 + t * (0.60 - 0.75)


K_PEEL = 0.50
"""
Peel factor applied when load has an out-of-plane component. (Assumption A3)
Peel loading significantly reduces effective joint strength. Conservative estimate.
"""

K_ZZ = 0.70
"""
Zigzag stitch penalty K_zz. (Assumption A4)
Zigzag stitches have apex stress concentrations at reversal points.
Applied to zigzag stitch count only. Straight rows use K_zz = 1.0.
Conservative estimate. Calibrate with stitch pattern comparison tests.
"""

K_LOOP = 0.50
"""
Loop joint load split factor. (Assumption A5)
For loop joints, load is distributed across two webbing legs.
Applied to the *demand* side (input load), not tack strength.
Assumes symmetric load distribution between legs.
"""

K_FOLD_EDGE = 0.85
"""
Fold edge stress concentration for loop joints. (Assumption A6)
The fold creates a stress concentration at the fold-side short edge of the tack.
Applied only to that edge's contribution in the tear-out calculation.
Conservative estimate. Validate with folded specimen tests.
"""


# =============================================================================
# FAILURE MODE: THREAD SHEAR
# =============================================================================

def calc_thread_shear(thread: Thread, geometry: TackGeometry,
                      peel: bool) -> tuple:
    """
    Calculate thread shear/tensile failure strength.

    This is the primary governing failure mode for webbing-on-webbing joints
    and the most reliable output of this tool.

    Formula:
        F = (N_straight * F_break * K_sl * K_angle [* K_peel])
          + (N_zigzag  * F_break * K_sl * K_angle [* K_peel] * K_zz)

    Returns (strength_n, detail_dict)
    """
    k_sl = k_shear_lag(geometry.aspect_ratio())
    k_ang = k_load_angle(geometry.load_angle_deg)
    k_peel = K_PEEL if peel else 1.0

    n_str = geometry.total_straight_stitches()
    n_zz = geometry.total_zigzag_stitches()
    f_break = thread.breaking_strength_n

    f_straight = n_str * f_break * k_sl * k_ang * k_peel
    f_zigzag = n_zz * f_break * k_sl * k_ang * k_peel * K_ZZ

    strength = f_straight + f_zigzag

    detail = {
        "k_sl": round(k_sl, 3),
        "k_angle": round(k_ang, 3),
        "k_peel": round(k_peel, 3),
        "k_zz": K_ZZ,
        "n_straight_stitches": n_str,
        "n_zigzag_stitches": n_zz,
        "f_straight_n": round(f_straight, 1),
        "f_zigzag_n": round(f_zigzag, 1),
    }
    return strength, detail


# =============================================================================
# FAILURE MODE: TEAR-OUT
# =============================================================================

def calc_tear_out(webbing: Webbing, geometry: TackGeometry) -> tuple:
    """
    Calculate webbing tear-out failure strength.

    IMPORTANT MODEL LIMITATION (A8): Tear-out in practice initiates at a single
    point of stress concentration and propagates progressively. The full perimeter
    never carries load simultaneously. This model assumes simultaneous full-perimeter
    failure and therefore produces an OPTIMISTIC (UPPER-BOUND) estimate.
    If tear-out governs, treat the result with additional caution.

    For lap joints:
        F = perimeter * shear_strength_per_mm * layer_count

    For loop joints:
        The fold-side short edge has a stress concentration (K_FOLD_EDGE).
        Both webbing legs contribute; layer_count includes both legs.

    Returns (strength_n, detail_dict)
    """
    s = webbing.shear_strength_n_per_mm
    L = geometry.tack_length_mm
    W = geometry.tack_width_mm
    layers = geometry.layer_count

    if geometry.joint_type == "lap":
        perimeter = 2.0 * (L + W)
        strength = perimeter * s * layers
        fold_reduction_applied = False

    elif geometry.joint_type == "loop":
        # Two long edges + one free short edge (full strength)
        # + one fold-side short edge (reduced by K_FOLD_EDGE, assumption A6)
        perimeter_full = 2.0 * L + W          # two long edges + one short
        perimeter_fold = W * K_FOLD_EDGE       # fold-side short edge, reduced
        effective_perimeter = perimeter_full + perimeter_fold
        strength = effective_perimeter * s * layers
        fold_reduction_applied = True
    else:
        raise ValueError(f"Unknown joint_type '{geometry.joint_type}'")

    detail = {
        "shear_strength_n_per_mm": round(s, 4),
        "shear_derived_von_mises": webbing.shear_derived,
        "tack_length_mm": L,
        "tack_width_mm": W,
        "layer_count": layers,
        "fold_reduction_applied": fold_reduction_applied,
        "k_fold_edge": K_FOLD_EDGE if fold_reduction_applied else None,
        "upper_bound": True,
    }
    return strength, detail


# =============================================================================
# CALCULATOR
# =============================================================================

@dataclass
class BartackResult:
    # Inputs (for report)
    joint_type: str
    thread_name: str
    webbing_name: str
    tack_length_mm: float
    tack_width_mm: float
    layer_count: int
    load_angle_deg: float
    peel: bool
    safety_factor: float

    # Failure mode outputs
    thread_shear_n: float
    tear_out_n: float
    thread_shear_detail: dict
    tear_out_detail: dict

    # Governing result
    governing_mode: str
    design_strength_n: float
    allowable_load_n: float

    # Warnings
    warnings: list

    # Derived
    @property
    def design_strength_lbf(self) -> float:
        return from_newtons(self.design_strength_n, "lbf")

    @property
    def allowable_load_lbf(self) -> float:
        return from_newtons(self.allowable_load_n, "lbf")

    @property
    def tear_out_lbf(self) -> float:
        return from_newtons(self.tear_out_n, "lbf")

    @property
    def thread_shear_lbf(self) -> float:
        return from_newtons(self.thread_shear_n, "lbf")


def run_calculator(
    thread: Thread,
    webbing: Webbing,
    geometry: TackGeometry,
    peel: bool,
    safety_factor: float,
) -> BartackResult:
    """
    Assemble all inputs, evaluate both failure paths, return governing result.
    """
    warnings = []

    # --- Assumption flags ---
    if thread.elongation_assumed:
        warnings.append(
            "A7: Thread elongation at break assumed 0.20 (default). "
            "Use published spec when available."
        )
    if webbing.shear_derived:
        warnings.append(
            "A1: Webbing shear strength derived from tensile via von Mises "
            f"(0.577x tensile/width = {webbing.shear_strength_n_per_mm:.3f} N/mm). "
            "Not measured. Obtain from manufacturer or direct test."
        )
    if peel:
        warnings.append(
            "A3: Peel factor 0.50 applied. Peel loading significantly reduces "
            "joint strength. Validate with peel-geometry-specific testing."
        )
    if geometry.joint_type == "loop":
        warnings.append(
            "A5: Loop joint: load split 50/50 across two webbing legs assumed "
            "(symmetric). Verify fold geometry is symmetric in application."
        )
        warnings.append(
            "A6: Fold-edge stress concentration factor 0.85 applied to "
            "tear-out calculation at fold side."
        )

    # --- Failure mode calculations ---
    f_thread, thread_detail = calc_thread_shear(thread, geometry, peel)
    f_tearout, tearout_detail = calc_tear_out(webbing, geometry)

    # --- Governing mode ---
    if f_thread <= f_tearout:
        governing = "Thread Shear"
        design_strength = f_thread
    else:
        governing = "Tear-Out"
        design_strength = f_tearout
        warnings.append(
            "A8: TEAR-OUT IS THE GOVERNING MODE. The tear-out model assumes "
            "simultaneous full-perimeter failure. In practice, tear-out initiates "
            "progressively at a stress concentration point. This result is an "
            "UPPER BOUND. Prioritize destructive testing before relying on this value."
        )

    warnings.append(
        "A2: Shear lag K_sl is a conservative estimate based on end-stitch "
        "stress concentration analogy. Tack width is assumed to approximate "
        "webbing width. Results are less reliable if tack width is substantially "
        "less than webbing width."
    )

    allowable = design_strength / safety_factor

    return BartackResult(
        joint_type=geometry.joint_type,
        thread_name=thread.name,
        webbing_name=webbing.name,
        tack_length_mm=geometry.tack_length_mm,
        tack_width_mm=geometry.tack_width_mm,
        layer_count=geometry.layer_count,
        load_angle_deg=geometry.load_angle_deg,
        peel=peel,
        safety_factor=safety_factor,
        thread_shear_n=f_thread,
        tear_out_n=f_tearout,
        thread_shear_detail=thread_detail,
        tear_out_detail=tearout_detail,
        governing_mode=governing,
        design_strength_n=design_strength,
        allowable_load_n=allowable,
        warnings=warnings,
    )


# =============================================================================
# REPORT
# =============================================================================

def format_report(r: BartackResult) -> str:
    lines = []
    lines.append("=" * 50)
    lines.append("  BARTACK DESIGN STRENGTH REPORT")
    lines.append("=" * 50)
    lines.append("")
    lines.append("NOTE: Webbing-on-webbing joints only.")
    lines.append("      All results require destructive test validation.")
    lines.append("")
    lines.append("--- Inputs ---")
    lines.append(f"  Joint Type       : {r.joint_type.upper()}")
    lines.append(f"  Thread           : {r.thread_name}")
    lines.append(f"  Webbing          : {r.webbing_name}")
    lines.append(
        f"  Tack Dimensions  : {r.tack_length_mm:.1f} mm x {r.tack_width_mm:.1f} mm"
        f"  ({from_mm(r.tack_length_mm, 'in'):.3f} in x "
        f"{from_mm(r.tack_width_mm, 'in'):.3f} in)"
    )
    lines.append(f"  Layers           : {r.layer_count}")
    lines.append(f"  Load Angle       : {r.load_angle_deg:.1f} deg")
    lines.append(f"  Peel Loading     : {'Yes' if r.peel else 'No'}")
    lines.append("")
    lines.append("--- Correction Factors (Thread Shear) ---")
    d = r.thread_shear_detail
    lines.append(f"  K_sl  (shear lag)   : {d['k_sl']:.3f}")
    lines.append(f"  K_ang (load angle)  : {d['k_angle']:.3f}")
    lines.append(f"  K_peel              : {d['k_peel']:.3f}")
    lines.append(f"  K_zz  (zigzag pen.) : {d['k_zz']:.2f}  "
                 f"(applied to {d['n_zigzag_stitches']} zigzag stitches)")
    lines.append(f"  Straight stitches   : {d['n_straight_stitches']}")
    lines.append("")
    lines.append("--- Failure Mode Results ---")
    lines.append(
        f"  Thread Shear  : {r.thread_shear_n:>9,.1f} N  "
        f"({r.thread_shear_lbf:>7,.1f} lbf)"
    )
    tearout_flag = "  [UPPER BOUND]" if r.tear_out_detail.get("upper_bound") else ""
    lines.append(
        f"  Tear-Out      : {r.tear_out_n:>9,.1f} N  "
        f"({r.tear_out_lbf:>7,.1f} lbf){tearout_flag}"
    )
    lines.append("")

    if r.governing_mode == "Tear-Out":
        lines.append("  *** WARNING: TEAR-OUT GOVERNS — UPPER BOUND RESULT ***")
        lines.append("  *** Validate with destructive testing.             ***")
        lines.append("")

    lines.append(f"  Governing Mode   : {r.governing_mode}")
    lines.append(
        f"  Design Strength  : {r.design_strength_n:>9,.1f} N  "
        f"({r.design_strength_lbf:>7,.1f} lbf)"
    )
    lines.append("")
    lines.append(f"  Safety Factor    : {r.safety_factor:.1f}")
    lines.append(
        f"  Allowable Load   : {r.allowable_load_n:>9,.1f} N  "
        f"({r.allowable_load_lbf:>7,.1f} lbf)"
    )
    lines.append("")
    lines.append("--- Warnings & Assumptions ---")
    for i, w in enumerate(r.warnings, 1):
        # Wrap long warnings at 70 chars
        import textwrap
        wrapped = textwrap.fill(w, width=68, subsequent_indent="       ")
        lines.append(f"  [{i}] {wrapped}")
    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)


def result_to_json(r: BartackResult) -> str:
    """Serialize result to JSON for piping to other scripts."""
    data = {
        "inputs": {
            "joint_type": r.joint_type,
            "thread": r.thread_name,
            "webbing": r.webbing_name,
            "tack_length_mm": r.tack_length_mm,
            "tack_width_mm": r.tack_width_mm,
            "layer_count": r.layer_count,
            "load_angle_deg": r.load_angle_deg,
            "peel": r.peel,
            "safety_factor": r.safety_factor,
        },
        "failure_modes": {
            "thread_shear_n": round(r.thread_shear_n, 2),
            "thread_shear_lbf": round(r.thread_shear_lbf, 2),
            "tear_out_n": round(r.tear_out_n, 2),
            "tear_out_lbf": round(r.tear_out_lbf, 2),
            "tear_out_upper_bound": True,
        },
        "result": {
            "governing_mode": r.governing_mode,
            "design_strength_n": round(r.design_strength_n, 2),
            "design_strength_lbf": round(r.design_strength_lbf, 2),
            "allowable_load_n": round(r.allowable_load_n, 2),
            "allowable_load_lbf": round(r.allowable_load_lbf, 2),
        },
        "correction_factors": r.thread_shear_detail,
        "warnings": r.warnings,
    }
    return json.dumps(data, indent=2)


# =============================================================================
# INTERACTIVE MODE
# =============================================================================

def prompt(msg: str, default=None) -> str:
    if default is not None:
        msg = f"{msg} [{default}]: "
    else:
        msg = f"{msg}: "
    val = input(msg).strip()
    if val == "" and default is not None:
        return str(default)
    return val


def interactive_mode() -> BartackResult:
    print()
    print("=" * 50)
    print("  BARTACK DESIGN STRENGTH CALCULATOR")
    print("=" * 50)
    print()
    print("NOTE: This tool models webbing-on-webbing joints only.")
    print("      Not valid for webbing-to-fabric joints.")
    print()

    # Joint type
    while True:
        jt = prompt("Joint type (lap / loop)").lower()
        if jt in ("lap", "loop"):
            break
        print("  Enter 'lap' or 'loop'.")

    # Thread
    print()
    print("Available threads:")
    for line in list_available_threads():
        print(f"  {line}")
    while True:
        t_key = prompt("Thread size (e.g. 69, 138)")
        try:
            thread = get_thread(t_key)
            break
        except ValueError as e:
            print(f"  {e}")

    # Webbing
    print()
    print("Available webbings:")
    for line in list_available_webbings():
        print(f"  {line}")
    while True:
        w_key = prompt("Webbing key (e.g. 1in_nylon_flat)")
        try:
            webbing = get_webbing(w_key)
            break
        except ValueError as e:
            print(f"  {e}")

    print()
    print("Tack dimensions — enter value with unit, e.g. '1.0 in' or '25.4 mm'")

    while True:
        try:
            tl = parse_value_unit(prompt("Tack length (load axis)"), "length")
            break
        except ValueError as e:
            print(f"  {e}")

    while True:
        try:
            tw = parse_value_unit(prompt("Tack width (across webbing)"), "length")
            break
        except ValueError as e:
            print(f"  {e}")

    while True:
        try:
            n_str = int(prompt("Number of straight stitch rows", default=4))
            break
        except ValueError:
            print("  Enter an integer.")

    while True:
        try:
            n_zz = int(prompt("Number of zigzag passes", default=2))
            break
        except ValueError:
            print("  Enter an integer.")

    while True:
        try:
            pitch = parse_value_unit(prompt("Stitch pitch", default="2.0 mm"), "length")
            break
        except ValueError as e:
            print(f"  {e}")

    while True:
        try:
            layers = int(prompt("Layer count (total webbing layers through tack)", default=2))
            break
        except ValueError:
            print("  Enter an integer.")

    while True:
        try:
            angle = float(prompt("Load angle (degrees from tack long axis)", default=0))
            break
        except ValueError:
            print("  Enter a number.")

    peel_str = prompt("Peel loading present? (y/n)", default="n").lower()
    peel = peel_str in ("y", "yes")

    while True:
        try:
            sf = float(prompt("Safety factor", default=3.0))
            if sf <= 0:
                raise ValueError()
            break
        except ValueError:
            print("  Enter a positive number.")

    geometry = TackGeometry(
        joint_type=jt,
        tack_length_mm=tl,
        tack_width_mm=tw,
        n_straight_rows=n_str,
        n_zigzag_passes=n_zz,
        stitch_pitch_mm=pitch,
        layer_count=layers,
        webbing_thickness_mm=webbing.thickness_mm,
        load_angle_deg=angle,
    )

    return run_calculator(thread, webbing, geometry, peel, sf)


# =============================================================================
# ARGPARSE / MAIN
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bartack.py",
        description=(
            "Bartack design strength calculator. "
            "Models thread shear and tear-out failure paths for "
            "webbing-on-webbing bartack joints. "
            "Run without arguments for interactive mode."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Unit strings: mm, cm, in, ft  (length)  |  N, kN, lbf, kip  (force)\n"
            "Value+unit examples: '1.0 in'  '25.4 mm'  '2 mm'\n\n"
            "SCOPE: Webbing-on-webbing joints only.\n"
            "All outputs are design estimates. Validate by destructive testing."
        ),
    )

    p.add_argument("--joint", choices=["lap", "loop"],
                   help="Joint type: lap or loop (folded end)")
    p.add_argument("--thread", metavar="SIZE",
                   help="Thread size designation (e.g. 69, 138, 207)")
    p.add_argument("--webbing", metavar="KEY",
                   help="Webbing key (e.g. 1in_nylon_flat). Use --list-webbings.")
    p.add_argument("--tack-length", metavar="'VAL UNIT'",
                   help="Tack length along load axis (e.g. '1.0 in')")
    p.add_argument("--tack-width", metavar="'VAL UNIT'",
                   help="Tack width across webbing (e.g. '0.5 in')")
    p.add_argument("--straight-rows", type=int, default=4,
                   help="Number of straight stitch rows (default: 4)")
    p.add_argument("--zigzag-passes", type=int, default=2,
                   help="Number of zigzag passes (default: 2)")
    p.add_argument("--stitch-pitch", metavar="'VAL UNIT'", default="2.0 mm",
                   help="Stitch pitch center-to-center (default: '2.0 mm')")
    p.add_argument("--layers", type=int, default=2,
                   help="Total webbing layers through tack (default: 2)")
    p.add_argument("--load-angle", type=float, default=0.0,
                   help="Load angle in degrees from tack long axis (default: 0)")
    p.add_argument("--peel", action="store_true",
                   help="Flag: peel loading is present")
    p.add_argument("--safety-factor", type=float, default=3.0,
                   help="Safety factor applied to design strength (default: 3.0)")
    p.add_argument("--output", choices=["human", "json"], default="human",
                   help="Output format: human-readable report or JSON (default: human)")
    p.add_argument("--list-threads", action="store_true",
                   help="List available thread keys and exit")
    p.add_argument("--list-webbings", action="store_true",
                   help="List available webbing keys and exit")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --- List commands ---
    if args.list_threads:
        print("Available threads:")
        for line in list_available_threads():
            print(f"  {line}")
        sys.exit(0)

    if args.list_webbings:
        print("Available webbings:")
        for line in list_available_webbings():
            print(f"  {line}")
        sys.exit(0)

    # --- Decide mode: argparse or interactive ---
    required = [args.joint, args.thread, args.webbing,
                args.tack_length, args.tack_width]

    if not any(required):
        # No required args provided — run interactive
        result = interactive_mode()
    else:
        # Argparse mode — validate all required args present
        missing = []
        if not args.joint:       missing.append("--joint")
        if not args.thread:      missing.append("--thread")
        if not args.webbing:     missing.append("--webbing")
        if not args.tack_length: missing.append("--tack-length")
        if not args.tack_width:  missing.append("--tack-width")
        if missing:
            parser.error(f"Missing required arguments: {', '.join(missing)}")

        try:
            thread = get_thread(args.thread)
            webbing = get_webbing(args.webbing)
            tl = parse_value_unit(args.tack_length, "length")
            tw = parse_value_unit(args.tack_width, "length")
            pitch = parse_value_unit(args.stitch_pitch, "length")
        except ValueError as e:
            parser.error(str(e))

        geometry = TackGeometry(
            joint_type=args.joint,
            tack_length_mm=tl,
            tack_width_mm=tw,
            n_straight_rows=args.straight_rows,
            n_zigzag_passes=args.zigzag_passes,
            stitch_pitch_mm=pitch,
            layer_count=args.layers,
            webbing_thickness_mm=webbing.thickness_mm,
            load_angle_deg=args.load_angle,
        )

        result = run_calculator(
            thread, webbing, geometry,
            peel=args.peel,
            safety_factor=args.safety_factor,
        )

    # --- Output ---
    output_fmt = getattr(args, "output", "human")
    if output_fmt == "json":
        print(result_to_json(result))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()
