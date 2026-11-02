# RAPID-Orbit-Simulator

Hosts simulation/visualisation scripts for various cases.

Sims with ```if __name__ ==  "__main__":``` will be called using plotly and displayed on the associated
github pages

## Local Testing

To setup for local testing (will install all relevant dependencies and fix module import errors), run
```[python]
pip install -e .
```

## Development

Relative to the other two repositories this one has very few strict coding standards.

In order to access code within the RAPID-Software submodule, python scripts need
a pretty verbose import script (AFTER ALL OTHER IMPORTS)

```[python]
# ... any other imports
from output import publish # This import is necessary for github pages integration

REPO_ROOT = Path(__file__).resolve().parents[2] # effectively 'cd ../../'
sys.path.insert(0, str(REPO_ROOT / "submodules" / "RAPID-Software" / "src" / "lib"))

from sun_model import vec_satellite_to_sun
```

An output script also needs to be written. Note that publish() formats the output for both 
github pages and local environments. An example is shown:

```[python]
def sun_orbit_test():
    """Test script that shows the TLE's full orbit"""
    t_min, jd, fr, r_teme = propagate_orbit(EX_TLE1, EX_TLE2, n_steps=180)
    sun_xyz = sat_to_sun_series(jd, fr, r_teme)
    fig = plot_orbit(t_min, r_teme, sun_xyz, show=False)
    publish(fig, "Sun Vector (Full Orbit)", out_dir = "sun_models")
    
if __name__ == "__main__":
    sun_orbit_test()
```


