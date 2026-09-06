"""Verify the notebook the way Colab actually loads it.

The previous check joined each cell's `source` list with "\\n", which silently RE-ADDED the
newlines the file was missing — so it passed on a notebook whose every code cell was collapsed
onto one line. Two guards against that recurring:

  1. structural — assert every source element except the last ends with a newline, and validate
     against the real nbformat schema
  2. behavioural — execute the notebook through nbclient, which is what Jupyter and Colab do

Run this after any change to 50_build_notebook.py.
"""
import json, pathlib, sys, time
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

NB = pathlib.Path(__file__).parent.parent / "notebook" / "olist_promise_problem.ipynb"
raw = json.loads(NB.read_text(encoding="utf-8"))

print("=" * 74)
print("1. STRUCTURE")
print("=" * 74)
bad = [(i, j) for i, c in enumerate(raw["cells"])
       for j, l in enumerate(c["source"][:-1]) if not l.endswith("\n")]
print(f"  cells                                {len(raw['cells'])}")
print(f"  code cells                           {sum(1 for c in raw['cells'] if c['cell_type'] == 'code')}")
print(f"  source lines missing trailing \\n     {len(bad)}")
if bad:
    print(f"  FAIL - first offender: cell {bad[0][0]}, line {bad[0][1]}")
    sys.exit(1)

nb = nbformat.read(str(NB), as_version=4)
nbformat.validate(nb)
print("  nbformat.validate                    OK")

# The decisive check: concatenate exactly as Jupyter does and compile each code cell.
for i, c in enumerate(nb.cells):
    if c.cell_type != "code":
        continue
    src = "".join(c.source) if isinstance(c.source, list) else c.source
    try:
        compile(src, f"<cell {i}>", "exec")
    except SyntaxError as e:
        print(f"  FAIL - cell {i} does not compile: {e}")
        print("  " + src[:200])
        sys.exit(1)
print("  every code cell compiles             OK")

print()
print("=" * 74)
print("2. EXECUTION  (nbclient — the same path Colab takes)")
print("=" * 74)
t0 = time.time()
client = NotebookClient(nb, timeout=1800, kernel_name="python3",
                        resources={"metadata": {"path": str(NB.parent.parent)}})
try:
    client.execute()
except CellExecutionError as e:
    print(f"  FAIL after {time.time() - t0:.0f}s\n{e}")
    sys.exit(1)

errs = [(i, o) for i, c in enumerate(nb.cells) if c.cell_type == "code"
        for o in c.get("outputs", []) if o.get("output_type") == "error"]
print(f"  executed {sum(1 for c in nb.cells if c.cell_type == 'code')} code cells "
      f"in {time.time() - t0:.0f}s")
print(f"  cells raising errors                 {len(errs)}")
if errs:
    i, o = errs[0]
    print(f"  FAIL - cell {i}: {o.get('ename')}: {o.get('evalue')}")
    sys.exit(1)

figs = sum(1 for c in nb.cells if c.cell_type == "code"
           for o in c.get("outputs", []) if "image/png" in o.get("data", {}))
print(f"  figures rendered                     {figs}")
print("\n  PASS - the notebook runs top to bottom with no errors.")
