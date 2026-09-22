#!/usr/bin/env python3
import argparse,json,sqlite3
from pathlib import Path

def query(con,sql): return [dict(r) for r in con.execute(sql)]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("database"); ap.add_argument("--output"); a=ap.parse_args(); con=sqlite3.connect(a.database); con.row_factory=sqlite3.Row
    errors=[]; warnings=[]; checks={}; integrity=con.execute("PRAGMA integrity_check").fetchone()[0]; checks["sqlite_integrity"]=integrity
    if integrity!="ok": errors.append("SQLite integrity check failed")
    months=[r[0] for r in con.execute("SELECT DISTINCT year_month FROM population ORDER BY 1")]; checks["months"]=months
    if len(months)!=12: errors.append(f"Expected 12 months, found {len(months)}")
    manifest_errors=[]
    try:
        manifest=json.loads(Path(a.database).with_name("dataset_manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest,dict): raise ValueError("manifest must be an object")
        if manifest.get("available_months")!=sorted({m[:7] for m in months}):
            manifest_errors.append("available_months does not match database")
        for key,expected_value in (("dataset","縣市人口數按性別及年齡"),("dimensions",["month","region","sex","age"]),("measures",["population"]),("unsupported",["income","occupation","birth_count","migration_count","causal_explanations"])):
            if manifest.get(key)!=expected_value: manifest_errors.append(f"Invalid manifest {key}")
    except (OSError,ValueError) as e:
        manifest_errors.append(str(e))
    checks["manifest_failures"]=manifest_errors
    errors.extend(manifest_errors)
    bad=query(con,"SELECT year_month,region_name,COUNT(DISTINCT sex) n FROM population WHERE age_label='all' GROUP BY 1,2 HAVING n<>2"); checks["sex_completeness_failures"]=bad[:20]
    if bad: errors.append(f"Sex completeness failures: {len(bad)}")
    bad=query(con,"SELECT year_month,region_name,sex,COUNT(*) n FROM population WHERE age_label<>'all' GROUP BY 1,2,3 HAVING n<>101"); checks["age_coverage_failures"]=bad[:20]
    if bad: errors.append(f"Age coverage failures: {len(bad)}")
    bad=query(con,"SELECT p.year_month,p.region_name,p.sex,p.population overall,SUM(x.population) age_sum FROM population p JOIN population x ON x.year_month=p.year_month AND x.region_name=p.region_name AND x.sex=p.sex AND x.age_label<>'all' WHERE p.age_label='all' GROUP BY 1,2,3,4 HAVING overall<>age_sum"); checks["age_reconciliation_failures"]=bad[:20]
    if bad: errors.append(f"Age reconciliation failures: {len(bad)}")
    bad=query(con,"SELECT t.year_month,t.region_name,t.population supplied,SUM(p.population) calculated FROM source_region_total t JOIN population p ON p.year_month=t.year_month AND p.region_name=t.region_name AND p.age_label='all' GROUP BY 1,2,3 HAVING supplied<>calculated"); checks["source_total_failures"]=bad[:20]
    if bad: errors.append(f"Supplied total failures: {len(bad)}")
    expected=con.execute("SELECT COUNT(DISTINCT year_month||'|'||region_name) FROM population WHERE age_label='all'").fetchone()[0]; supplied=con.execute("SELECT COUNT(*) FROM source_region_total").fetchone()[0]
    if supplied<expected: warnings.append(f"{expected-supplied} source total rows absent; computed totals remain available")
    components="'臺北市','新北市','桃園市','臺中市','臺南市','高雄市','臺灣省','福建省'"
    bad=query(con,f"WITH n AS (SELECT year_month,SUM(population) v FROM population WHERE region_name='總計' AND age_label='all' GROUP BY 1), c AS (SELECT year_month,SUM(population) v FROM population WHERE region_name IN ({components}) AND age_label='all' GROUP BY 1) SELECT n.year_month,n.v national,c.v components FROM n JOIN c USING(year_month) WHERE n.v<>c.v"); checks["geographic_reconciliation_failures"]=bad
    if bad: errors.append(f"Geographic reconciliation failures: {len(bad)}")
    status="failed" if errors else ("passed_with_warnings" if warnings else "passed"); result={"status":status,"checks":checks,"warnings":warnings,"errors":errors}; text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: Path(a.output).write_text(text+"\n",encoding="utf-8")
    print(text); raise SystemExit(1 if errors else 0)
if __name__=="__main__": main()
