#!/usr/bin/env python3
import argparse,csv,json,re,sqlite3
from pathlib import Path
import xlrd

def clean(v): return re.sub(r"\s+","",str(v or "")).replace("　","")
def integer(v):
    if v in (None,""): raise ValueError("missing numeric cell")
    n=int(float(v))
    if n<0: raise ValueError("negative population")
    return n
def header(s):
    for r in range(min(10,s.nrows)):
        vals=[clean(s.cell_value(r,c)) for c in range(s.ncols)]
        has_zero=any(isinstance(s.cell_value(r,c),(int,float)) and float(s.cell_value(r,c))==0 for c in range(s.ncols))
        prior=[clean(s.cell_value(r-1,c)) for c in range(s.ncols)] if r else []
        if has_zero and ("總計" in vals or "總計" in prior): return r
    raise ValueError(f"header not found: {s.name}")
def level(n): return "national" if n=="總計" else ("province" if n in ("臺灣省","福建省") else "local")
def month(s,hr):
    text=" ".join(clean(s.cell_value(r,c)) for r in range(min(hr+1,4)) for c in range(s.ncols)); m=re.search(r"(\d{3})年(\d{2})月底",text)
    if not m: raise ValueError(f"month not found: {s.name}")
    return f"{int(m.group(1))+1911:04d}-{int(m.group(2)):02d}-01"
def cols(s,hr):
    ages={int(s.cell_value(hr,c)):c for c in range(s.ncols) if isinstance(s.cell_value(hr,c),(int,float)) and float(s.cell_value(hr,c)).is_integer() and 0<=int(s.cell_value(hr,c))<=99}
    if set(ages)!=set(range(100)): raise ValueError(f"ages incomplete: {s.name}")
    explicit=[c for c in range(s.ncols) if clean(s.cell_value(hr,c)) in ("100+","100歲以上")]
    candidates=explicit or [c for c in range(max(ages.values())+1,s.ncols) if clean(s.cell_value(hr,c))==""]
    if len(candidates)!=1: raise ValueError(f"100+ not unique: {s.name}: {candidates}")
    return ages,candidates[0]
def parse(path):
    book=xlrd.open_workbook(path,formatting_info=True); facts=[]; totals=[]; warnings=[]
    for sn in book.sheet_names():
        s=book.sheet_by_name(sn); hr=header(s); ym=month(s,hr); ages,plus=cols(s,hr)
        for r in range(hr+1,s.nrows):
            if clean(s.cell_value(r,1))!="男" or not clean(s.cell_value(r,0)): continue
            name=clean(s.cell_value(r,0)); fr=r+1
            if fr>=s.nrows or clean(s.cell_value(fr,1))!="女": raise ValueError(f"female row missing after {name} in {sn}")
            for rr,sex in ((r,"male"),(fr,"female")):
                facts.append((ym,name,level(name),sex,None,"all",integer(s.cell_value(rr,2)),sn))
                facts.extend((ym,name,level(name),sex,a,str(a),integer(s.cell_value(rr,c)),sn) for a,c in ages.items())
                facts.append((ym,name,level(name),sex,None,"100+",integer(s.cell_value(rr,plus)),sn))
            if r>0 and clean(s.cell_value(r-1,1))=="計": totals.append((ym,name,integer(s.cell_value(r-1,2)),sn))
            else: warnings.append(f"{ym} {name}: supplied total row missing")
    return facts,totals,warnings
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("source"); ap.add_argument("--output-dir",required=True); a=ap.parse_args(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    facts,totals,warnings=parse(a.source); cp=out/"population_long.csv"; dp=out/"population.sqlite"
    with cp.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); w.writerow(["year_month","region_name","region_level","sex","age","age_label","population","source_sheet"]); w.writerows(facts)
    if dp.exists(): dp.unlink()
    con=sqlite3.connect(dp); con.executescript("CREATE TABLE population(year_month TEXT NOT NULL,region_name TEXT NOT NULL,region_level TEXT NOT NULL,sex TEXT NOT NULL CHECK(sex IN('male','female')),age INTEGER,age_label TEXT NOT NULL,population INTEGER NOT NULL CHECK(population>=0),source_sheet TEXT NOT NULL,PRIMARY KEY(year_month,region_name,sex,age_label)); CREATE TABLE source_region_total(year_month TEXT NOT NULL,region_name TEXT NOT NULL,population INTEGER NOT NULL,source_sheet TEXT NOT NULL,PRIMARY KEY(year_month,region_name)); CREATE INDEX idx_population_query ON population(year_month,region_level,region_name,sex,age);")
    con.executemany("INSERT INTO population VALUES(?,?,?,?,?,?,?,?)",facts); con.executemany("INSERT INTO source_region_total VALUES(?,?,?,?)",totals); con.commit(); integrity=con.execute("PRAGMA integrity_check").fetchone()[0]; con.close()
    manifest={
        "dataset":"縣市人口數按性別及年齡",
        "available_months":sorted({row[0][:7] for row in facts}),
        "dimensions":["month","region","sex","age"] if facts else [],
        "measures":["population"] if facts else [],
        "unsupported":["income","occupation","birth_count","migration_count","causal_explanations"],
    }
    mp=out/"dataset_manifest.json"
    mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"facts={len(facts)} source_totals={len(totals)} integrity={integrity}"); [print("WARNING:",x) for x in warnings]; print(cp.resolve()); print(dp.resolve()); print(mp.resolve())
if __name__=="__main__": main()
