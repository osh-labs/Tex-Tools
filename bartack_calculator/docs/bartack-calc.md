# Bartack Design Strength Calculator

The main script is `bartack_calculator/bartack_calc.py`. Run it directly with `python bartack_calculator/bartack_calc.py`.

Material properties are stored in `bartack_calculator/materials_library.json` so users can edit thread and webbing values without changing code.

The calculator evaluates three failure paths and reports the governing (minimum) design strength:

- Thread shear/tensile failure
- Webbing tear-out failure, capped at the webbing's tensile strength
- Webbing tensile failure at the stitch line (evaluated only when a measured joint efficiency is given)

Results are per joint: no per-leg load split is applied to loop joints.

It then applies a safety factor to provide allowable load.

## Scope and Safety

- Valid only for **webbing-on-webbing** joints.
- Not valid for webbing-to-fabric joints.
- Output is an engineering estimate, not certification data.
- Always validate results with destructive testing before design release.

## What the Script Models

The script includes:

- Material tables for bonded nylon thread sizes (`69`, `138`, `207`, `277`, `346`, `415`) loaded from JSON
- Material table for common webbing options (nylon/polyester/tubular/dyneema/polypro) loaded from JSON
- Geometric inputs for tack dimensions and stitch layout
- Correction factors for:
  - Shear lag (`K_sl`)
  - Load angle (`K_angle`)
  - Peel loading (`K_peel`)
  - Zigzag penalty (`K_zz`)
  - Loop fold-edge concentration (`K_fold_edge`)
- Governing mode selection and warnings for key assumptions (A1-A11)

## Failure modes

| Mode | Formula |
|---|---|
| Thread shear | `N_straight * F_break * K_sl * K_angle [* K_peel] + N_zigzag * F_break * K_sl * K_angle [* K_peel] * K_zz` |
| Tear-out (lap) | `min(2 (L + W) * s * n_side, T * n_side)` |
| Tear-out (loop) | `min((2 L + W + K_fold_edge W) * s * n_side, T * n_side)` |
| Webbing tensile | `T * eta * n_side` (only when `eta` is set) |

`s` = webbing shear strength per mm (A1: `0.577 T / width` when not measured), `T` = webbing
tensile strength, `n_side = max(1, layers // 2)` (A9), `eta` = joint efficiency (sewn-joint /
plain webbing tensile, 0-1, from destructive test; no default).

## Assumption codes

| Code | Meaning |
|---|---|
| A1 | Webbing shear strength derived from tensile via von Mises (0.577) |
| A2 | Shear lag `K_sl` is an estimate; tack width assumed close to webbing width |
| A3 | Peel factor 0.50 applied |
| A5 | Loop joint: result per joint (both legs together), no per-leg split |
| A6 | Fold-edge factor 0.85 on the fold-side edge (loop tear-out) |
| A8 | Tear-out governs: upper-bound result |
| A9 | Layers per side = layers // 2 (min 1); tear-out and webbing break run through one side |
| A10 | Tear-out capped at webbing tensile x layers per side (physical upper bound) |
| A11 | Webbing tensile mode not evaluated (joint efficiency not set) |

A4 (zigzag penalty) is applied in the thread shear formula and has no runtime warning. A7
(thread elongation) was removed: elongation does not enter any formula.

## Changes 2026-10-31

- Tear-out uses layers per side (`layers // 2`, min 1) instead of the total layer count.
- Tear-out is capped at webbing tensile strength x layers per side. Before the cap, tear-out
  values could exceed the webbing's own breaking strength (reference case: 18,480 N on a
  5,338 N webbing), so tear-out could not govern in practice.
- New mode: webbing tensile at the stitch line, `T * eta * n_side`. `eta` comes from
  `--joint-efficiency` or the webbing's `joint_efficiency` in the library (default `null`).
- `K_LOOP` removed. It was defined, and the A5 warning said it was applied, but no code used it.
  Results are per joint.
- A7 (thread elongation) warning removed.
- Reference vectors: `bartack_calculator/reference_vectors.py` / `reference_vectors.json`.

## Requirements

- Python 3.8+
- Rich (`pip install rich`) for improved terminal UI
- prompt_toolkit (`pip install prompt_toolkit`) for interactive autocompletion

If `rich` or `prompt_toolkit` are not installed, the script falls back to plain terminal prompts/output.

## Run Modes

### 1) Interactive mode

Run with no required CLI arguments:

```bash
python bartack_calculator/bartack_calc.py
```

The script prompts for all inputs and prints a formatted report.
Thread and webbing prompts support Tab autocompletion (keys and names) when `prompt_toolkit` is installed.

### 2) CLI / scriptable mode

Example:

```bash
python bartack_calculator/bartack_calc.py \
  --joint lap \
  --thread 69 \
  --webbing 1in_nylon_flat \
  --tack-length "1.0 in" \
  --tack-width "0.5 in" \
  --total-stitches 42 \
  --straight-rows 2 \
  --zigzag-passes 1 \
  --layers 2 \
  --load-angle 0 \
  --peel \
  --safety-factor 3.0 \
  --output human
```

## Key CLI Arguments

Required (for non-interactive mode):

- `--joint {lap,loop}`
- `--thread SIZE`
- `--webbing KEY`
- `--tack-length "VAL UNIT"`
- `--tack-width "VAL UNIT"`
- `--total-stitches COUNT`

Common optional:

- `--straight-rows` (default: `2`)
- `--zigzag-passes` (default: `1`)
- `--layers` (default: `2`)
- `--load-angle` (default: `0`)
- `--peel` (flag)
- `--safety-factor` (default: `3.0`)
- `--joint-efficiency ETA` (0-1; no default; enables the webbing tensile mode)
- `--output {human,json}` (default: `human`)
- `--list-threads`
- `--list-webbings`

## Units

Supported length units:

- `mm`, `cm`, `in`, `ft`

Supported force units:

- `N`, `kN`, `lbf`, `kip`

Value+unit examples:

- `"25.4 mm"`
- `"1.0 in"`
- `"2 mm"`

## Editing Material Properties

Edit `bartack_calculator/materials_library.json` to add or change material options.

- `threads` map key: thread selection key (example: `69`)
- `webbings` map key: webbing selection key (example: `1in_nylon_flat`)
- Set `shear_strength_n_per_mm` to `null` to auto-derive shear strength from tensile/width (A1)
- `joint_efficiency`: measured sewn-joint / plain webbing tensile ratio (0-1); `null` until measured
- Use valid JSON syntax (double quotes, commas, no trailing commas)

After edits, validate entries with:

```bash
python bartack_calculator/bartack_calc.py --list-threads
python bartack_calculator/bartack_calc.py --list-webbings
```

## Output

### Human report

Includes:

- Input summary
- Correction factors
- Thread shear and tear-out strengths
- Governing mode
- Design strength and allowable load
- Assumption and warning list

### JSON report

Use:

```bash
python bartack_calculator/bartack_calc.py ... --output json
```

Returns structured fields under:

- `inputs`
- `failure_modes`
- `result`
- `correction_factors`
- `warnings`

## Engineering Notes

- Tear-out result is explicitly treated as an **upper-bound** model.
- If tear-out governs, prioritize physical testing before reliance.
- Reliability decreases if tack width is much less than webbing width.

## Quick Validation Commands

Check the model against the stored reference vectors (regenerate with `--write` after an
intentional model change, in the same commit):

```bash
python3 -I bartack_calculator/reference_vectors.py
```

List available thread keys:

```bash
python bartack_calculator/bartack_calc.py --list-threads
```

List available webbing keys:

```bash
python bartack_calculator/bartack_calc.py --list-webbings
```

Print built-in help:

```bash
python bartack_calculator/bartack_calc.py --help
```

## File Layout

- `bartack_calculator/bartack_calc.py` - calculator entry point and implementation
- `bartack_calculator/materials_library.json` - user-editable material library
- `bartack_calculator/reference_vectors.py`, `reference_vectors.json` - model reference cases
- `README.md` - repository overview
