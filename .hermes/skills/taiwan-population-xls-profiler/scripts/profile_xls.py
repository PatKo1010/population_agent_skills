#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path
import xlrd

def clean(v): return re.sub(r"\s+", "", str(v or "")).replace("　", "")
def header_row(s):
    for r in range(min(10, s.nrows)):
        vals=[clean(s.cell_value(r,c)) for c in range(s.ncols)]
        has_zero=any(isinstance(s.cell_value(r,c),(int,float)) and float(s.cell_value(r,c))==0 for c in range(s.ncols))
        prior=[clean(s.cell_value(r-1,c)) for c in range(s.ncols)] if r else []
        if has_zero and ("總計" in vals or "總計" in prior): return r
    raise ValueError(f"Cannot detect header in sheet {s.name}")
def inspect(s):
    hr=header_row(s); ages={}; subtotals=[]
    for c in range(s.ncols):
        v=s.cell_value(hr,c)
        if isinstance(v,(int,float)) and float(v).is_integer() and 0<=int(v)<=99: ages[int(v)]=c
        elif "合計" in clean(v): subtotals.append(c)
    tail=[c for c in range(max(ages.values())+1,s.ncols) if clean(s.cell_value(hr,c)) in ("","100+")]
    regions=[]; missing=[]
    for r in range(hr+1,s.nrows):
        if clean(s.cell_value(r,1))=="男" and clean(s.cell_value(r,0)):
            name=clean(s.cell_value(r,0)); regions.append(name)
            if not (r>0 and clean(s.cell_value(r-1,1))=="計"): missing.append(name)
    title=" ".join(clean(s.cell_value(r,c)) for r in range(min(4,s.nrows)) for c in range(s.ncols))
    m=re.search(r"114年(\d{2})月底",title)
    return {"sheet":s.name,"rows":s.nrows,"columns":s.ncols,"header_row_1_based":hr+1,"month":int(m.group(1)) if m else None,"age_min":min(ages),"age_max":max(ages),"age_column_count":len(ages),"age_subtotal_columns":subtotals,"candidate_100_plus_columns":tail,"region_count":len(regions),"regions":regions,"regions_missing_source_total_row":missing,"merged_cell_count":len(s.merged_cells)}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("source"); ap.add_argument("--output"); a=ap.parse_args()
    book=xlrd.open_workbook(a.source,formatting_info=True); sheets=[]; errors=[]
    for n in book.sheet_names():
        try: sheets.append(inspect(book.sheet_by_name(n)))
        except Exception as e: errors.append({"sheet":n,"error":str(e)})
    result={"source":str(Path(a.source).resolve()),"sheet_count":len(book.sheet_names()),"sheets":sheets,"errors":errors}; text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: Path(a.output).write_text(text+"\n",encoding="utf-8")
    print(text); raise SystemExit(1 if errors else 0)
if __name__=="__main__": main()
