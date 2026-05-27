# Bartack Design Strength Calculator

This folder contains a single script, `bartack-calc.py`, used to estimate bartack joint strength for **webbing-on-webbing** joints.

The calculator evaluates two failure paths and reports the governing (minimum) design strength:

- Thread shear/tensile failure
- Webbing tear-out failure

It then applies a safety factor to provide allowable load.

## Scope and Safety

- Valid only for **webbing-on-webbing** joints.
- Not valid for webbing-to-fabric joints.
- Output is an engineering estimate, not certification data.
- Always validate results with destructive testing before design release.

## What the Script Models

The script includes:

- Material tables for bonded nylon thread sizes (`69`, `138`, `207`, `277`, `346`, `415`)
- Material table for common webbing options (nylon/polyester/tubular/dyneema/polypro)
- Geometric inputs for tack dimensions and stitch layout
- Correction factors for:
  - Shear lag (`K_sl`)
  - Load angle (`K_angle`)
  - Peel loading (`K_peel`)
  - Zigzag penalty (`K_zz`)
  - Loop fold-edge concentration (`K_fold_edge`)
- Governing mode selection and warnings for key assumptions (A1-A8)

## Requirements

- Python 3.8+
- Rich (`pip install rich`) for improved terminal UI
- prompt_toolkit (`pip install prompt_toolkit`) for interactive autocompletion

If `rich` or `prompt_toolkit` are not installed, the script falls back to plain terminal prompts/output.

## Run Modes

### 1) Interactive mode

Run with no required CLI arguments:

```bash
python bartack-calc.py
```

The script prompts for all inputs and prints a formatted report.
Thread and webbing prompts support Tab autocompletion (keys and names) when `prompt_toolkit` is installed.

### 2) CLI / scriptable mode

Example:

```bash
python bartack-calc.py \
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
python bartack-calc.py ... --output json
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

List available thread keys:

```bash
python bartack-calc.py --list-threads
```

List available webbing keys:

```bash
python bartack-calc.py --list-webbings
```

Print built-in help:

```bash
python bartack-calc.py --help
```

## File Layout

- `bartack-calc.py` - calculator implementation and CLI entry point
- `README.md` - usage and model notes
