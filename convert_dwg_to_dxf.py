from pathlib import Path
from ezdxf.addons import odafc

INPUT_DIR = Path("/Users/athulcharanthara/Downloads/testscript/files/dwg_in")
OUTPUT_DIR = Path("/Users/athulcharanthara/Downloads/testscript/files/dxf_out")

odafc.unix_exec_path = "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Using ODA path:", odafc.unix_exec_path)
print("Installed?", odafc.is_installed())

if not odafc.is_installed():
    raise RuntimeError(f"ODA File Converter not found at: {odafc.unix_exec_path}")

for dwg_file in INPUT_DIR.glob("*.dwg"):
    out_file = OUTPUT_DIR / f"{dwg_file.stem}.dxf"
    odafc.convert(
        source=dwg_file,
        dest=out_file,
        version="R2018",
        audit=True,
        replace=True,
    )
    print(f"Converted: {dwg_file.name} -> {out_file.name}")