# three.js — vendored, pinned

    three@0.186.0   (npm, MIT — see LICENSE)

Copied verbatim from the package, nothing modified:

| file | from |
|---|---|
| `three.module.js` | `build/three.module.js` |
| `three.core.js`   | `build/three.core.js` (imported relatively by the above) |
| `STLLoader.js`    | `examples/jsm/loaders/STLLoader.js` |
| `OrbitControls.js`| `examples/jsm/controls/OrbitControls.js` |

Pinned for the same reason `OCP.wasm` is: this renders the part the user is
about to print, and a floating version is a stranger's build deciding what
they see. ~432 KB gzipped in total, fetched only when the 3D preview is used.

The two `examples/jsm` files import the bare specifier `three`, resolved by the
import map in `index.html` — which is why that map must come before every
module script on the page, PyScript's included.

To update: bump the version here and in `tools/package.json`, re-copy the four
files, and re-run the viewer check in CLAUDE.md.
