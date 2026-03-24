"""
Canvas LMS Assignment Heat Map Generator
=========================================
Generates a calendar heat map showing:
  - GREEN: assignment was due AND submitted
  - RED:   assignment was due but NOT submitted
  - Color intensity increases with more assignments on that day

Requirements:  pip install requests matplotlib numpy
Usage:
  export CANVAS_URL="https://yourschool.instructure.com"
  export CANVAS_API_TOKEN="your_token_here"
  python canvas_heatmap.py
"""

import requests
import json
import os
from datetime import datetime, date, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
import calendar
import sys

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
# Set these as environment variables before running:
#   export CANVAS_URL="https://yourschool.instructure.com"
#   export CANVAS_API_TOKEN="your_token_here"
CANVAS_URL = os.environ.get("CANVAS_URL", "https://graniteschools.instructure.com")
API_TOKEN  = os.environ.get("CANVAS_API_TOKEN")
OUTPUT_FILE = "assignment_heatmap.png"

if not API_TOKEN:
    print("Error: CANVAS_API_TOKEN environment variable is not set.")
    print("Set it with:  export CANVAS_API_TOKEN=\"your_token_here\"")
    sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = f"{CANVAS_URL}/api/v1"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def paginate(url, params=None):
    """Handle Canvas API pagination."""
    results = []
    if params is None:
        params = {}
    params["per_page"] = 100
    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        results.extend(resp.json())
        links = resp.headers.get("Link", "")
        url = None
        params = {}
        for part in links.split(","):
            if 'rel="next"' in part:
                url = part.split("<")[1].split(">")[0]
    return results


def fetch_data():
    """Fetch all courses, assignments, and submission statuses."""
    print("Fetching active courses...")
    courses = paginate(f"{BASE_URL}/courses", {
        "enrollment_state": "active",
        "state[]": "available"
    })
    print(f"  Found {len(courses)} active courses.")

    all_assignments = []
    for course in courses:
        cid = course["id"]
        cname = course.get("name", f"Course {cid}")
        print(f"  Fetching assignments for: {cname}...")

        try:
            assignments = paginate(
                f"{BASE_URL}/courses/{cid}/assignments",
                {"order_by": "due_at", "include[]": "submission"}
            )
        except requests.exceptions.HTTPError as e:
            print(f"    Skipping (error: {e})")
            continue

        for a in assignments:
            due_at = a.get("due_at")
            if not due_at:
                continue

            sub = a.get("submission") or {}
            submitted_at = sub.get("submitted_at")
            workflow = sub.get("workflow_state", "unsubmitted")

            all_assignments.append({
                "course": cname,
                "name": a.get("name", "Unknown"),
                "due_at": due_at,
                "submitted_at": submitted_at,
                "submitted": workflow not in ("unsubmitted",) and submitted_at is not None,
            })

    print(f"\nTotal assignments with due dates: {len(all_assignments)}")
    return all_assignments


def build_day_data(assignments):
    """
    Build per-day counts:
      day -> {"submitted": int, "missing": int}
    """
    day_data = defaultdict(lambda: {"submitted": 0, "missing": 0})

    for a in assignments:
        due_str = a["due_at"]
        try:
            due_date = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()
        except ValueError:
            continue

        if a["submitted"]:
            day_data[due_date]["submitted"] += 1
        else:
            day_data[due_date]["missing"] += 1

    return day_data


def generate_heatmap(day_data, assignments):
    """Generate a GitHub-style calendar heat map."""

    if not day_data:
        print("No assignment data found! Check your courses and API token.")
        sys.exit(1)

    # Determine date range
    all_dates = list(day_data.keys())
    min_date = min(all_dates)
    max_date = max(all_dates)

    # Extend to full months
    min_date = min_date.replace(day=1)
    last_day = calendar.monthrange(max_date.year, max_date.month)[1]
    max_date = max_date.replace(day=last_day)

    # Build list of months
    months = []
    d = min_date
    while d <= max_date:
        months.append((d.year, d.month))
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)

    num_months = len(months)
    cols = min(4, num_months)
    rows = (num_months + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4.5, rows * 3.5))
    fig.suptitle("Canvas Assignment Heat Map", fontsize=18, fontweight="bold", y=0.98)

    # Flatten axes for easy indexing
    if num_months == 1:
        axes = np.array([axes])
    axes = np.array(axes).flatten()

    # Hide unused subplots
    for i in range(num_months, len(axes)):
        axes[i].set_visible(False)

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for idx, (year, month) in enumerate(months):
        ax = axes[idx]
        ax.set_title(f"{calendar.month_abbr[month]} {year}", fontsize=12, fontweight="bold", pad=8)
        ax.set_xlim(-0.5, 6.5)

        # Calendar grid
        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(year, month)
        num_weeks = len(weeks)
        ax.set_ylim(-0.5, num_weeks - 0.5)
        ax.invert_yaxis()

        # Day-of-week headers
        for i, name in enumerate(day_names):
            ax.text(i, -0.8, name, ha="center", va="center", fontsize=7, color="#666")

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)

        for week_idx, week in enumerate(weeks):
            for dow, day in enumerate(week):
                if day == 0:
                    continue

                current_date = date(year, month, day)
                info = day_data.get(current_date)

                if info is None:
                    # No assignment due — light gray background
                    color = "#f0f0f0"
                    text_color = "#999"
                elif info["missing"] > 0 and info["submitted"] == 0:
                    # All missing — red shades
                    intensity = min(info["missing"] / 3, 1.0)
                    r = 0.95
                    g = 0.95 - 0.6 * intensity
                    b = 0.95 - 0.6 * intensity
                    color = (r, g, b)
                    text_color = "#900" if intensity > 0.3 else "#c66"
                elif info["submitted"] > 0 and info["missing"] == 0:
                    # All submitted — green shades
                    intensity = min(info["submitted"] / 3, 1.0)
                    r = 0.95 - 0.55 * intensity
                    g = 0.95 - 0.1 * intensity
                    b = 0.95 - 0.55 * intensity
                    color = (r, g, b)
                    text_color = "#060" if intensity > 0.3 else "#6a6"
                else:
                    # Mix of submitted and missing — orange/amber
                    total = info["submitted"] + info["missing"]
                    miss_ratio = info["missing"] / total
                    intensity = min(total / 3, 1.0)
                    r = 0.95
                    g = 0.95 - 0.4 * intensity
                    b = 0.95 - 0.65 * intensity
                    color = (r, g, b)
                    text_color = "#a50"

                # Draw cell
                rect = mpatches.FancyBboxPatch(
                    (dow - 0.42, week_idx - 0.42), 0.84, 0.84,
                    boxstyle="round,pad=0.05",
                    facecolor=color,
                    edgecolor="#ddd",
                    linewidth=0.5,
                )
                ax.add_patch(rect)
                ax.text(dow, week_idx, str(day), ha="center", va="center",
                        fontsize=8, color=text_color, fontweight="bold" if info else "normal")

                # Small count indicator
                if info and (info["submitted"] + info["missing"]) > 1:
                    count = info["submitted"] + info["missing"]
                    ax.text(dow + 0.3, week_idx + 0.3, str(count),
                            ha="center", va="center", fontsize=5.5, color=text_color, alpha=0.7)

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor="#5cb85c", edgecolor="#ddd", label="Due & Submitted"),
        mpatches.Patch(facecolor="#d9534f", edgecolor="#ddd", label="Due & NOT Submitted"),
        mpatches.Patch(facecolor="#f0ad4e", edgecolor="#ddd", label="Mixed (some missing)"),
        mpatches.Patch(facecolor="#f0f0f0", edgecolor="#ddd", label="No assignments due"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=4,
               fontsize=9, frameon=True, fancybox=True, shadow=True,
               bbox_to_anchor=(0.5, 0.01))

    # Summary stats
    total = len(assignments)
    submitted = sum(1 for a in assignments if a["submitted"])
    missing = total - submitted
    pct = (submitted / total * 100) if total else 0
    fig.text(0.5, 0.04, f"Total: {total} assignments  |  Submitted: {submitted}  |  Missing: {missing}  |  Rate: {pct:.0f}%",
             ha="center", fontsize=10, color="#555")

    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(OUTPUT_FILE, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"\nHeat map saved to: {OUTPUT_FILE}")
    plt.close()


def main():
    assignments = fetch_data()
    day_data = build_day_data(assignments)
    generate_heatmap(day_data, assignments)

    # Also save a detailed breakdown
    report_file = "assignment_details.txt"
    with open(report_file, "w") as f:
        f.write("CANVAS ASSIGNMENT DETAILS\n")
        f.write("=" * 60 + "\n\n")
        for a in sorted(assignments, key=lambda x: x["due_at"]):
            status = "SUBMITTED" if a["submitted"] else "MISSING"
            due = datetime.fromisoformat(a["due_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            f.write(f"[{status:>9}]  {due}  {a['course']}: {a['name']}\n")
    print(f"Detail report saved to: {report_file}")


if __name__ == "__main__":
    main()
