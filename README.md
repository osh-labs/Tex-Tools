# Textile Engineering Scripts

This repository is a collection of textile engineering tools and scripts used for research and development of caving, climbing, and rescue gear.

Owner: Southeast Expedition Medical, LLC, Chris Lee

## Purpose

The goal of this repository is to support engineering exploration, prototyping, and early-stage analysis of sewn and textile-based hardware systems.

These tools are intended to help with:

- Design iteration
- Parameter studies
- Preliminary strength estimates
- Documentation of engineering assumptions

## Current Contents

- `bartack-calc.py`: Bartack design strength calculator for webbing-on-webbing joints
- `bartack-calc.md`: Detailed usage and model notes for the bartack calculator

## Safety and Liability Notice

These scripts are provided for research and engineering development purposes only.

- No warranty is provided, express or implied.
- The authors and contributors assume no liability for any direct, indirect, incidental, special, exemplary, or consequential damages arising from use of this repository.
- Outputs are engineering estimates and are not certification data.
- Physical testing, validation, and professional engineering judgment are required before any field use.

Use of these scripts is entirely at your own risk.

## License

This repository is licensed under the GNU General Public License, version 3 or any later version (GPL-3.0-or-later).

See the full license text in `LICENSE`.

Copyleft intent:

- Derivative works must remain open source under GPL-compatible terms.
- Source code for derivative distributions must be made available under the same license obligations.

## Contributions

Contributions are welcome if they improve model clarity, engineering transparency, and safety margins.

When contributing:

- Clearly document assumptions and limits
- Prefer conservative defaults in safety-relevant calculations
- Include validation notes when changing equations or factors

### Source File Header Framework

Contributors should include a source header in new scripts and modules. Use this template and update the placeholders:

```text
#!/usr/bin/env python3
# <file-name> - <short description>
# Copyright (C) <year> Southeast Expedition Medical, LLC, Chris Lee
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
```

## Status

This repository is under active engineering development. Interfaces, assumptions, and models may change over time.
