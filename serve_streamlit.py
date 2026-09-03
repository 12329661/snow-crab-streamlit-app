import shlex
import subprocess
from pathlib import Path

import modal

# ## Define container dependencies
#
# `app.py` imports pandas/plotly/seaborn/matplotlib/streamlit/python-dotenv/supabase,
# so we include those in the image and then add the `app.py` file itself.

streamlit_script_local_path = Path(__file__).parent / "app.py"
streamlit_script_remote_path = "/root/app.py"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "streamlit~=1.62.0",
        "pandas~=3.0.5",
        "plotly~=6.9.0",
        "seaborn~=0.13.2",
        "matplotlib~=3.11.1",
        "supabase~=2.31.0",
        "python-dotenv~=1.2.3",
    )
    .add_local_file(streamlit_script_local_path, streamlit_script_remote_path)
)

app = modal.App(name="mfsnowcrab-streamlit", image=image)

if not streamlit_script_local_path.exists():
    raise RuntimeError(
        "app.py not found! Place the script with your streamlit app in the same directory."
    )

# ## Spawning the Streamlit server
#
# The Supabase credentials come from the `supabase-credentials` Modal secret
# (see `modal secret create supabase-credentials ...`), which is injected as
# environment variables into the container — `app.py` reads them via
# `os.environ`, same as it does locally from `.env`.


@app.function(secrets=[modal.Secret.from_name("supabase-credentials")])
@modal.concurrent(max_inputs=100)
@modal.web_server(8000)
def run():
    target = shlex.quote(streamlit_script_remote_path)
    cmd = f"streamlit run {target} --server.port 8000 --server.enableCORS=false --server.enableXsrfProtection=false"
    subprocess.Popen(cmd, shell=True)


# ## Iterate and deploy
#
#   modal serve serve_streamlit.py    # ephemeral, live-reloads on file change
#   modal deploy serve_streamlit.py   # persistent deployment, prints a public URL
