import hashlib
import json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import xlrd

SOURCE = Path('/Users/patrick/Downloads/縣市人口數按性別及年齡-114年.xls')
OUT = Path(__file__).parent
book = xlrd.open_workbook(str(SOURCE))
data = {}
checks = 0

def clean(v):
    return ''.join(str(v).split())

def colname(c):
    out = ''
    c += 1
    while c:
        c, r = divmod(c - 1, 26)
        out = chr(65 + r) + out
    return out

for sheet in book.sheets():
    header = next(r for r in range(5) if sum(isinstance(v, float) and 0 <= v <= 99 for v in sheet.row_values(r)) == 100)
    ages = {int(v): c for c, v in enumerate(sheet.row_values(header)) if isinstance(v, float) and 0 <= v <= 99}
    hundred = [c for c in range(sheet.ncols) if any(clean(sheet.cell_value(r, c)) == '100+' for r in range(header + 1))]
    rows = {}
    for r in range(header + 1, sheet.nrows - 2):
        if clean(sheet.cell_value(r, 1)) != '計':
            continue
        region = clean(sheet.cell_value(r + 1, 0))
        assert region
        for off, sex in enumerate(['計', '男', '女']):
            assert clean(sheet.cell_value(r + off, 1)) == sex
            rows[region, sex] = r + off
        for c in range(2, sheet.ncols):
            vals = [sheet.cell_value(r + off, c) for off in range(3)]
            assert all(isinstance(v, float) and v >= 0 and v == int(v) for v in vals)
            assert vals[0] == vals[1] + vals[2]
            checks += 1
        for off in range(3):
            # December's unlabeled terminal column is checked numerically only;
            # it is never assigned an age or used in age-specific answers.
            tail = hundred[0] if hundred else sheet.ncols - 1
            assert sheet.cell_value(r + off, 2) == sum(sheet.cell_value(r + off, c) for c in ages.values()) + sheet.cell_value(r + off, tail)
            checks += 1
        # Independently reconcile printed five-year subtotals with single ages.
        for c in range(3, sheet.ncols):
            if clean(sheet.cell_value(header, c)) == '合計':
                for off in range(3):
                    assert sheet.cell_value(r + off, c) == sum(sheet.cell_value(r + off, k) for k in range(c + 1, c + 6))
                    checks += 1
    counties = sorted({region for region, sex in rows if region not in ['總計', '臺灣省', '福建省']})
    assert len(counties) == 22
    for sex in ['計', '男', '女']:
        for c in [2, *ages.values(), *(hundred or [sheet.ncols - 1])]:
            assert sheet.cell_value(rows['總計', sex], c) == sum(sheet.cell_value(rows[reg, sex], c) for reg in counties)
            checks += 1
    data[int(sheet.name)] = (sheet, ages, hundred, rows, counties)

def operand(month, region='總計', sex='計', lo=None, hi=None):
    sheet, ages, hundred, rows, _ = data[month]
    r = rows[region, sex]
    if lo is None:
        cols = [2]
        scope = '全年齡（原表總計欄）'
    else:
        cols = [ages[a] for a in range(lo, min(hi, 99) + 1)]
        if hi == 100:
            assert hundred, 'Unlabeled terminal column cannot support a 100+ answer'
            cols += hundred
        scope = f'{lo}–{hi}歲（含端點）' if hi != 100 else f'{lo}歲以上（含100+）'
    cells = [{'cell': f'{colname(c)}{r+1}', 'value': int(sheet.cell_value(r, c))} for c in cols]
    return {'month': f'2025-{month:02}', 'region': region, 'sex': sex, 'age_scope': scope, 'sheet': sheet.name,
            'cells': cells, 'value': sum(c['value'] for c in cells)}

items = []
def add(category, question, operation, ops):
    values = [o['value'] for o in ops]
    if operation == 'identity':
        expected = values[0]
        answer = f'{expected:,} 人'
        unit = '人'
    elif operation == 'difference':
        expected = values[1] - values[0]
        answer = f'{expected:+,} 人（後月減前月）'
        unit = '人'
    elif operation == 'percent':
        expected = float((Decimal(values[0]) / Decimal(values[1]) * 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
        answer = f'{expected:.2f}%（{values[0]:,} ÷ {values[1]:,} × 100）'
        unit = '%'
    else:
        top = max(values) if operation == 'maximum' else min(values)
        expected = [{'region': o['region'], 'population': o['value']} for o in ops if o['value'] == top]
        answer = '、'.join(f"{e['region']}：{e['population']:,} 人" for e in expected)
        unit = '人'
    items.append({'id': f'G{len(items)+1:03}', 'category': category, 'question': question,
                  'answer': answer, 'expected': expected, 'unit': unit, 'operation': operation,
                  'absolute_tolerance': 0.005 if operation == 'percent' else 0, 'operands': ops})

for m in range(1, 13):
    add('全國月末總人口', f'民國114年{m}月底，全國不分性別、全年齡人口共有多少人？', 'identity', [operand(m)])

for m, reg, sex in [(1,'臺北市','男'),(12,'新北市','女'),(6,'桃園市','計'),(12,'臺中市','男'),(3,'臺南市','女'),(9,'高雄市','計'),(12,'新竹縣','計'),(12,'新竹市','計')]:
    add('縣市與性別', f'民國114年{m}月底，{reg}{ {"男":"男性","女":"女性","計":"不分性別"}[sex]}的全年齡人口是多少人？', 'identity', [operand(m,reg,sex)])

for m, reg, sex, lo, hi in [(1,'總計','計',0,0),(12,'總計','計',0,14),(12,'總計','計',15,64),(11,'總計','計',65,100),(11,'總計','計',100,100),(6,'臺北市','女',65,100),(12,'桃園市','男',0,14),(3,'高雄市','計',20,39),(9,'金門縣','計',80,100),(12,'連江縣','女',65,99)]:
    scope = f'{lo}至{hi}歲（含端點）' if hi != 100 else ('100歲以上' if lo == 100 else f'{lo}歲以上（含100歲以上）')
    add('年齡條件', f'民國114年{m}月底，{"全國" if reg == "總計" else reg}{ {"男":"男性","女":"女性","計":"不分性別"}[sex]}{scope}人口是多少人？', 'identity', [operand(m,reg,sex,lo,hi)])

for m, reg, sex, lo, hi in [(12,'總計','女',None,None),(12,'臺北市','女',None,None),(12,'總計','計',0,14),(12,'總計','計',15,64),(11,'總計','計',65,100),(11,'臺北市','計',65,100),(6,'新竹縣','計',0,14),(6,'連江縣','男',None,None)]:
    num = operand(m,reg,sex,lo,hi)
    label = {'女':'女性全年齡人口','男':'男性全年齡人口','計':num['age_scope']+'人口'}[sex]
    add('人口比例', f'民國114年{m}月底，{"全國" if reg == "總計" else reg}的{label}占該地區不分性別全年齡總人口百分之多少？四捨五入至小數點後2位。', 'percent', [num,operand(m,reg)])

for m, sex, lo, hi, operation in [(12,'計',None,None,'maximum'),(12,'計',None,None,'minimum'),(6,'女',None,None,'maximum'),(11,'計',65,100,'maximum'),(12,'計',0,14,'maximum'),(11,'計',100,100,'minimum')]:
    ops = [operand(m,reg,sex,lo,hi) for reg in data[m][4]]
    scope = ops[0]['age_scope']
    add('縣市排名', f'民國114年{m}月底，22個縣市中（排除全國、臺灣省及福建省彙總列），{ {"女":"女性","計":"不分性別"}[sex]}{scope}人口{"最多" if operation == "maximum" else "最少"}的是哪些縣市、各有多少人？並列者全部列出。', operation, ops)

for a,b,reg,sex,lo,hi in [(1,12,'總計','計',None,None),(1,12,'新北市','計',None,None),(1,12,'桃園市','計',None,None),(6,12,'臺北市','女',None,None),(1,12,'總計','計',0,14),(1,11,'總計','計',65,100)]:
    ops = [operand(m,reg,sex,lo,hi) for m in [a,b]]
    add('跨月增減', f'民國114年{b}月底相較{a}月底，{"全國" if reg == "總計" else reg}{ {"女":"女性","計":"不分性別"}[sex]}{ops[0]["age_scope"]}人口增減多少人？以後月減前月，保留正負號。', 'difference', ops)

selected_ids = [1, 6, 12, 13, 14, 19, 20, 21, 24, 25, 30, 31, 33, 35, 39, 40, 44, 45, 47, 50]
items = [items[i - 1] for i in selected_ids]
for i, q in enumerate(items, 1):
    q["original_id"] = q["id"]
    q["id"] = f"G{i:03}"
assert len(items) == 20
metadata = {'source': str(SOURCE), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'method': 'Independent direct XLS extraction with xlrd; no skill pipeline code, derived dataset, or query outputs used.',
            'year': 2025, 'roc_year': 114, 'question_count': len(items), 'source_reconciliation_assertions': checks,
            'warnings': ['12月最後一個數值欄無標籤；不將該欄解讀為100歲以上，不產生12月65歲以上等依賴該欄的答案。',
                         '月末人口存量不是出生數或全年累計人數；跨月差額不是出生或死亡人數。'],
            'grading': 'Counts and signed changes: exact integers. Percentages: compare numeric expected with absolute tolerance 0.005 percentage points; displayed values use decimal ROUND_HALF_UP to 2 places. Ranking: compare unordered complete tie set of region/population pairs.'}
payload = {'metadata': metadata, 'questions': items}
(OUT/'golden_set_20.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
with (OUT/'questions_only.jsonl').open('w') as f:
    for q in items:
        f.write(json.dumps({'id':q['id'],'question':q['question']},ensure_ascii=False)+'\n')
lines = ['# 民國114年人口 Golden Set：20題與標準答案', '',
         '來源：縣市人口數按性別及年齡-114年.xls。民國114年＝2025年；各月份均為月底人口，單位為人。', '',
         '依此次直接讀檔要求，答案由原始 XLS 獨立擷取及計算，未使用待測 skill pipeline。這是可重現的參考答案集，並非外部官方另行認證的答案。', '',
         f'核對：通過 {checks:,} 項來源內部加總斷言，涵蓋男女加總、單齡與總計、五歲組小計及22縣市與全國總計。', '',
         '限制：12月最後一個數值欄沒有標籤，因此12月題目不推定該欄為100歲以上；全國與縣市總人口直接採用有標籤的總計欄。', '',
         '評分：整數精確相等；百分比四捨五入至小數點後2位（容許誤差0.005個百分點）；排名比對完整並列集合，不要求並列項目順序。跨月人口差額不能解讀為出生或死亡人數。', '',
         'JSON 附每題結構化答案、運算方式、月份、地區、性別、年齡範圍，以及所有來源儲存格與原始值。questions_only.jsonl 可直接作為不含答案的測試輸入。', '',
         '| ID | 類型 | 題目 | 標準答案 |', '|---|---|---|---|']
for q in items:
    lines.append(f"| {q['id']} | {q['category']} | {q['question']} | {q['answer']} |")
(OUT/'golden_set_20.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'questions':len(items), 'checks':checks,'outputs':[str(OUT/n) for n in ['golden_set_20.md','golden_set_20.json','questions_only.jsonl']]},ensure_ascii=False))
