"""Stream the 9 sheets out of the delivered .xlsx into CSVs (one pass, low memory)."""
import csv, time, openpyxl, pathlib

SRC = r"C:\Users\varad\Downloads\Document from singhlink4.xlsx"
OUT = pathlib.Path(r"D:\Data Analytics Hackathon - Gradient\data\raw")
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
for ws in wb.worksheets:
    dest = OUT / f"{ws.title}.csv"
    n = 0
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for row in ws.iter_rows(values_only=True):
            w.writerow(["" if v is None else v for v in row])
            n += 1
    print(f"{ws.title:<22} {n:>9,} rows  ->  {dest.name}  [{time.time()-t0:6.1f}s]", flush=True)
wb.close()
print(f"DONE in {time.time()-t0:.1f}s")
