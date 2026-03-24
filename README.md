# Canvas Assignment Heat Map

Generates a calendar heat map from your Canvas LMS assignments, showing which were submitted on time and which were missed.

![example](https://img.shields.io/badge/output-PNG_heat_map-green)

## Colors

| Color | Meaning |
|-------|---------|
| 🟩 Green | Assignment due & submitted |
| 🟥 Red | Assignment due & **not** submitted |
| 🟧 Orange | Mixed — some submitted, some missing |
| ⬜ Gray | No assignments due |

Intensity scales with the number of assignments on that day.

## Setup

1. Install dependencies:

   ```bash
   pip install requests matplotlib numpy
   ```

2. Get a Canvas API token:
   - Log into Canvas → Account → Settings → **+ New Access Token**

3. Set environment variables:

   ```bash
   export CANVAS_URL="https://yourschool.instructure.com"
   export CANVAS_API_TOKEN="your_token_here"
   ```

4. Run:

   ```bash
   python canvas_heatmap.py
   ```

## Output

- `assignment_heatmap.png` — calendar heat map image
- `assignment_details.txt` — line-by-line breakdown of every assignment and its status
