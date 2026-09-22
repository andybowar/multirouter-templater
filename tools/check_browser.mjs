// Run the browser half of the app for real, outside a browser.
//
// The deployed site is Python on WebAssembly, so the interesting failures -
// a wheel that will not resolve, an OpenCascade call that is missing from the
// WASM build, an engraving with no font to draw it with - cannot be found by
// running the code on a workstation. This drives the same Pyodide that
// PyScript 2026.7.3 ships, against the same vendored bootstrap and the same
// bundled font, and exports one of everything.
//
//     npm install pyodide@314.0.3
//     node tools/check_browser.mjs
//
// Expect the first run to take a few minutes: it downloads ~23 MB of
// OpenCascade and then actually meshes a part.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (p) => readFileSync(join(ROOT, p));

const py = await loadPyodide();
const FS = py.FS;

// Lay out the filesystem the way pyscript.toml does.
FS.mkdir("/home/pyodide/app");
for (const name of ["__init__", "config", "geometry", "report", "model"]) {
  FS.writeFile(`/home/pyodide/app/${name}.py`, read(`app/${name}.py`));
}
FS.writeFile(
  "/home/pyodide/ocp_wasm_bootstrap.py",
  read("web/vendor/ocp_wasm_bootstrap.py"),
);
FS.mkdir("/mrtt-fonts");
FS.writeFile("/mrtt-fonts/DejaVuSans.ttf", read("web/fonts/DejaVuSans.ttf"));

await py.loadPackage("micropip");

console.log("installing build123d + OCP.wasm ...");
await py.runPythonAsync(`
import ocp_wasm_bootstrap
await ocp_wasm_bootstrap.bootstrap()
`);

console.log("building and exporting ...");
const summary = await py.runPythonAsync(`
import json

from app.geometry import Spec, spec_from_inputs
from app import model

# The factory calibration point, checked inside the browser runtime too.
spec = spec_from_inputs({"bit_dia": 0.5, "tenon_width": 0.5, "tenon_length": 2.0})
assert abs(spec.prof_wid_nom - 0.6250) < 1e-9, spec.prof_wid_nom
assert abs(spec.prof_len_nom - 2.1250) < 1e-9, spec.prof_len_nom

model.FONT_PATHS.append("/mrtt-fonts/DejaVuSans.ttf")
engraved = model._text_sketch(spec) is not None

out = {"engraving": engraved, "sizes": {}}
for fmt in ["stl", "step", "3mf", "dxf"]:
    data = model.export_bytes(spec, fmt, engrave=engraved)
    out["sizes"][fmt] = len(data)

# Binary STL: 84 byte header, then 50 bytes per triangle.
stl = model.export_bytes(spec, "stl", engrave=False)
out["triangles"] = int.from_bytes(stl[80:84], "little")
out["stl_well_formed"] = len(stl) == 84 + 50 * out["triangles"]

json.dumps(out)
`);

const result = JSON.parse(summary);
console.log(result);

const problems = [];
if (!result.engraving) problems.push("bundled font did not produce an engraving");
if (!result.stl_well_formed) problems.push("binary STL length does not match its triangle count");
for (const [fmt, size] of Object.entries(result.sizes)) {
  if (size < 1000) problems.push(`${fmt} export is suspiciously small (${size} bytes)`);
}

if (problems.length) {
  console.error("\nFAILED:\n  " + problems.join("\n  "));
  process.exit(1);
}
console.log("\nbrowser runtime ok");
