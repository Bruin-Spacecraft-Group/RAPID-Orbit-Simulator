"""
Helper Script to generate HTML for the simulations workflow and still
have compatibility locally

Call with publish()
"""

import os
from pathlib import Path

def publish(fig, name, show_locally=True, out_dir="output"):
    """save into an HTML file; also will open the sim in a browser when running locally."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig.write_html(out / f"{name}.html", include_plotlyjs="cdn")

    on_ci = os.environ.get("CI", "").lower() == "true"
    if show_locally and not on_ci:
        fig.show()
