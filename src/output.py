"""
Helper Script to generate HTML for the simulations workflow and still
have compatibility locally

Call with publish_plotly() or publish_czml()
"""

import json
import os
import tempfile
import webbrowser
from html import escape
from pathlib import Path

CESIUM_VERSION = "1.120"  # bump to the current CesiumJS release if you like


def _on_ci():
    return os.environ.get("CI", "").lower() == "true"


def publish_plotly(fig, name, show_locally=True, out_dir="output"):
    """save into an HTML file; also will open the sim in a browser when running locally."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig.write_html(out / f"{name}.html", include_plotlyjs="cdn")

    if show_locally and not _on_ci():
        fig.show()


_CESIUM_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<script src="https://cesium.com/downloads/cesiumjs/releases/__VER__/Build/Cesium/Cesium.js"></script>
<link href="https://cesium.com/downloads/cesiumjs/releases/__VER__/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
<style>html,body,#c{width:100%;height:100%;margin:0;overflow:hidden;background:#000}</style>
</head>
<body>
<div id="c"></div>
<script>
const TOKEN = __TOKEN__;
const czml = __CZML__;
const opts = { shouldAnimate: true };
if (TOKEN) {
  Cesium.Ion.defaultAccessToken = TOKEN;
} else {
  // No ion token: use OpenStreetMap imagery + a plain ellipsoid so nothing needs an account
  opts.baseLayer = new Cesium.ImageryLayer(
    new Cesium.OpenStreetMapImageryProvider({ url: "https://tile.openstreetmap.org/" }));
  opts.baseLayerPicker = false;
}
const viewer = new Cesium.Viewer("c", opts);
viewer.scene.globe.enableLighting = true;   // day/night terminator follows the sim clock
Cesium.CzmlDataSource.load(czml).then(ds => {
  viewer.dataSources.add(ds);
  viewer.zoomTo(ds);
});
</script>
</body>
</html>
"""


def publish_czml(packets, name, show_locally=True, out_dir="output",
                 save_czml=True, ion_token=None):
    """Publish a standalone CesiumJS viewer (CZML embedded in the page).

    - On GitHub (CI=true): writes <out_dir>/<name>.html (plus <name>.czml when
      save_czml is True) for the Pages workflow. Nothing is opened.
    - Locally: nothing is written into the repo. The viewer is written to a
      temporary directory and opened in the default browser (like fig.show()).
      With show_locally=False it does nothing.
    - The CZML is embedded in the page, so it works from file:// and as a static
      Pages file with no extra fetch.
    - ion_token defaults to the CESIUM_ION_TOKEN env var. With no token the viewer
      falls back to OpenStreetMap imagery. NOTE: the token is written into the HTML,
      so on a public Pages site use a token scoped to your Pages URL.
    Returns the path of the HTML file written, or None if nothing was written.
    """
        
    if not _on_ci() and not show_locally:
            return None

    czml_text = json.dumps(packets, separators=(",", ":"))
    token = ion_token if ion_token is not None else os.environ.get("CESIUM_ION_TOKEN", "")
    print(token)
    page = (_CESIUM_HTML
            .replace("__TITLE__", escape(name))
            .replace("__VER__", CESIUM_VERSION)
            .replace("__TOKEN__", json.dumps(token))
            .replace("__CZML__", czml_text.replace("</", "<\\/")))

    if _on_ci():
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        html_path = out / f"{name}.html"
        html_path.write_text(page, encoding="utf-8")
        if save_czml:
            (out / f"{name}.czml").write_text(czml_text, encoding="utf-8")
        return html_path

    html_path = Path(tempfile.mkdtemp(prefix="czml_viewer_")) / f"{name}.html"
    html_path.write_text(page, encoding="utf-8")
    webbrowser.open(html_path.as_uri())
    return html_path