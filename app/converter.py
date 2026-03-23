from pathlib import Path
import os
import shutil

from ezdxf.addons import odafc
from ezdxf.addons.odafc import UnknownODAFCError

oda_path = (
    shutil.which("ODAFileConverter")
    or shutil.which("ODADrawingsExplorer")
    or "/usr/bin/ODAFileConverter"
)

odafc.unix_exec_path = oda_path
odafc.xvfb_run = shutil.which("xvfb-run") or "/usr/bin/xvfb-run"


def _prepare_headless_env():
    runtime_dir = Path("/tmp/xdg-runtime")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.chmod(0o700)

    os.environ["XDG_RUNTIME_DIR"] = str(runtime_dir)
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")


def convert_dwg_to_dxf_in_place(input_dir: Path, output_dir: Path) -> list[Path]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _prepare_headless_env()

    print("Using ODA path:", odafc.unix_exec_path)
    print("Using xvfb-run:", odafc.xvfb_run)
    print("Using XDG_RUNTIME_DIR:", os.environ.get("XDG_RUNTIME_DIR"))
    print("Installed?", odafc.is_installed())

    if not odafc.is_installed():
        raise RuntimeError(f"ODA executable not found at: {odafc.unix_exec_path}")

    converted_files = []

    for dwg_file in input_dir.glob("*.dwg"):
        out_file = output_dir / f"{dwg_file.stem}.dxf"

        try:
            odafc.convert(
                source=dwg_file,
                dest=out_file,
                version="R2018",
                audit=True,
                replace=True,
            )
        except UnknownODAFCError as e:
            if not out_file.exists() or out_file.stat().st_size == 0:
                raise RuntimeError(f"DWG to DXF conversion failed for {dwg_file.name}: {e}") from e

        if not out_file.exists() or out_file.stat().st_size == 0:
            raise RuntimeError(f"ODA reported success but no DXF was created for {dwg_file.name}")

        converted_files.append(out_file)

    return converted_files