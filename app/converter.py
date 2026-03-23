from pathlib import Path
import shutil
from ezdxf.addons import odafc

oda_path = (
    shutil.which("ODAFileConverter")
    or shutil.which("ODADrawingsExplorer")
    or "/usr/bin/ODAFileConverter"
)

odafc.unix_exec_path = oda_path
odafc.xvfb_run = shutil.which("xvfb-run") or "/usr/bin/xvfb-run"


def convert_dwg_to_dxf_in_place(input_dir: Path, output_dir: Path) -> list[Path]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Using ODA path:", odafc.unix_exec_path)
    print("Using xvfb-run:", odafc.xvfb_run)
    print("Installed?", odafc.is_installed())

    if not odafc.is_installed():
        raise RuntimeError(f"ODA executable not found at: {odafc.unix_exec_path}")

    converted_files = []

    for dwg_file in input_dir.glob("*.dwg"):
        out_file = output_dir / f"{dwg_file.stem}.dxf"
        odafc.convert(
            source=dwg_file,
            dest=out_file,
            version="R2018",
            audit=True,
            replace=True,
        )
        converted_files.append(out_file)

    return converted_files