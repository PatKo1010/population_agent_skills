#!/usr/bin/env python3
"""Validate a JSON intent before running a fixed, parameterized population query."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

OPERATIONS = {'population_lookup', 'population_rank', 'population_trend', 'population_share'}
COMMON = {'operation', 'sex', 'region_level', 'age', 'age_min', 'age_max', 'include_100_plus'}
FIELDS = {
    'population_lookup': COMMON | {'month', 'region'},
    'population_rank': COMMON | {'month', 'limit'},
    'population_trend': COMMON | {'months', 'region'},
    'population_share': COMMON | {'month', 'limit'},
}


class Rejected(ValueError):
    def __init__(self, code, requested=None, status='invalid_intent', **details):
        self.payload = dict(status=status, code=code, requested=requested, **details, results=None)
        super().__init__(code)


def reject(code, requested=None, **details):
    raise Rejected(code, requested, **details)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            reject('DUPLICATE_FIELD', key)
        result[key] = value
    return result


def validate_intent(intent):
    if not isinstance(intent, dict):
        reject('INTENT_MUST_BE_OBJECT', intent)
    op = intent.get('operation')
    if not isinstance(op, str) or op not in OPERATIONS:
        reject('OPERATION_NOT_ALLOWED', op, status='out_of_scope', allowed=sorted(OPERATIONS))
    unknown = sorted(set(intent) - FIELDS[op])
    if unknown:
        reject('UNKNOWN_FIELDS', unknown)
    required = {'sex', 'region_level', 'months' if op == 'population_trend' else 'month'}
    if op in {'population_lookup', 'population_trend'}:
        required.add('region')
    missing = sorted(required - set(intent))
    if missing:
        reject('MISSING_REQUIRED_FIELDS', missing, status='needs_clarification')
    if intent['sex'] not in ('male', 'female', 'total'):
        reject('INVALID_SEX', intent['sex'])
    level = intent['region_level']
    if isinstance(level, list):
        reject('MIXED_GEOGRAPHIC_LEVELS', level)
    if level not in ('national', 'province', 'local'):
        reject('INVALID_REGION_LEVEL', level)
    if 'region' in intent and (not isinstance(intent['region'], str) or not intent['region']):
        reject('INVALID_REGION', intent['region'])
    months = intent['months'] if op == 'population_trend' else [intent['month']]
    if not isinstance(months, list) or not months or any(not isinstance(m, str) for m in months):
        reject('INVALID_MONTHS', months)
    if len(set(months)) != len(months):
        reject('DUPLICATE_MONTHS', months)
    if op == 'population_trend' and months != sorted(months):
        reject('MONTHS_NOT_CHRONOLOGICAL', months)
    if 'limit' in intent and (type(intent['limit']) is not int or not 1 <= intent['limit'] <= 1000):
        reject('INVALID_LIMIT', intent['limit'])
    range_fields = {'age_min', 'age_max', 'include_100_plus'} & set(intent)
    if 'age' in intent:
        if range_fields:
            reject('CONFLICTING_AGE_FILTERS', intent)
        value = intent['age']
        if value != '100+' and (type(value) is not int or not 0 <= value <= 99):
            reject('AGE_PRECISION_NOT_SUPPORTED', value, status='out_of_scope', supported=['0-99', '100+'])
    elif range_fields:
        missing = sorted({'age_min', 'include_100_plus'} - set(intent))
        if missing:
            reject('MISSING_REQUIRED_FIELDS', missing, status='needs_clarification')
        lo, hi = intent['age_min'], intent.get('age_max', 99)
        if type(lo) is not int or type(hi) is not int or not 0 <= lo <= hi <= 99:
            reject('INVALID_AGE_RANGE', {'age_min': lo, 'age_max': hi}, supported=['0-99', '100+'])
        if type(intent['include_100_plus']) is not bool:
            reject('INVALID_INCLUDE_100_PLUS', intent['include_100_plus'])
        if intent['include_100_plus'] and hi != 99:
            reject('CONFLICTING_AGE_FILTERS', intent)
    return months


def validate_dataset(con, database, intent, requested_months):
    months = [r[0] for r in con.execute('SELECT DISTINCT substr(year_month,1,7) FROM population ORDER BY 1')]
    try:
        manifest = json.loads(Path(database).with_name('dataset_manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        reject('INVALID_MANIFEST', status='data_error', message=str(exc))
    if (not isinstance(manifest, dict) or manifest.get('available_months') != months
            or manifest.get('dimensions') != ['month', 'region', 'sex', 'age']
            or manifest.get('measures') != ['population']):
        reject('INVALID_MANIFEST', status='data_error')
    for month in requested_months:
        if month not in months:
            reject('MONTH_NOT_AVAILABLE', month, status='out_of_scope',
                   available_range=[months[0], months[-1]] if months else [], available_months=months)
        rows = list(con.execute('SELECT DISTINCT region_name,region_level FROM population WHERE year_month=?', (month + '-01',)))
        region = intent.get('region')
        if region is not None:
            matches = [row for row in rows if row['region_name'] == region]
            if not matches:
                reject('REGION_NOT_AVAILABLE', region, status='out_of_scope', month=month,
                       available_regions=sorted(row['region_name'] for row in rows if row['region_level'] == intent['region_level']))
            if any(row['region_level'] != intent['region_level'] for row in matches):
                reject('REGION_LEVEL_MISMATCH', region, region_level=intent['region_level'])
        elif not any(row['region_level'] == intent['region_level'] for row in rows):
            reject('REGION_LEVEL_NOT_AVAILABLE', intent['region_level'], status='out_of_scope', month=month)


def execute_query(con, intent, months):
    """Only called after validation. SQL fragments below are developer-owned constants."""
    conditions = ['region_level=?', 'year_month IN (' + ','.join('?' for _ in months) + ')']
    params = [intent['region_level']] + [month + '-01' for month in months]
    if 'region' in intent:
        conditions.append('region_name=?')
        params.append(intent['region'])
    if intent['sex'] != 'total':
        conditions.append('sex=?')
        params.append(intent['sex'])
    if 'age' in intent:
        age_sql, age_params = 'age_label=?', [str(intent['age'])]
    elif 'age_min' in intent:
        age_sql = '(age BETWEEN ? AND ?)'
        age_params = [intent['age_min'], intent.get('age_max', 99)]
        if intent['include_100_plus']:
            age_sql = '(' + age_sql + " OR age_label='100+')"
    else:
        age_sql, age_params = "age_label='all'", []
    base = 'WITH scoped AS (SELECT * FROM population WHERE ' + ' AND '.join(conditions) + ') '
    if intent['operation'] == 'population_share':
        sql = base + '''SELECT year_month,region_name,
            SUM(CASE WHEN ''' + age_sql + ''' THEN population END) numerator,
            SUM(CASE WHEN age_label='all' THEN population END) denominator
            FROM scoped GROUP BY year_month,region_name'''
        rows = [dict(row) for row in con.execute(sql, params + age_params)]
        for row in rows:
            numerator, denominator = row['numerator'], row['denominator']
            if numerator is None or denominator is None:
                reject('NO_DATA', status='data_error')
            if denominator == 0:
                reject('ZERO_DENOMINATOR', row['region_name'], status='data_error')
            if not 0 <= numerator <= denominator:
                reject('INVALID_POPULATION_TOTALS', row['region_name'], status='data_error')
            row['percentage'] = round(100.0 * numerator / denominator, 4)
        rows.sort(key=lambda row: (-row['percentage'], row['region_name']))
        return rows[:intent.get('limit', 10)]
    sql = base + 'SELECT year_month,region_name,SUM(population) population FROM scoped WHERE ' + age_sql + ' GROUP BY year_month,region_name'
    if intent['operation'] == 'population_rank':
        sql += ' ORDER BY population DESC,region_name LIMIT ?'
        age_params.append(intent.get('limit', 10))
    else:
        sql += ' ORDER BY year_month,region_name'
    return [dict(row) for row in con.execute(sql, params + age_params)]


def query(database, intent):
    months = validate_intent(intent)
    con = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        validate_dataset(con, database, intent, months)
        rows = execute_query(con, intent, months)
        if not rows or (intent['operation'] == 'population_trend' and len(rows) != len(months)):
            reject('NO_DATA', intent, status='out_of_scope')
        return {'status': 'ok', 'intent': intent, 'results': rows}
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('--intent', required=True, help='JSON file path, or - to read stdin')
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.intent == '-' else Path(args.intent).read_text(encoding='utf-8')
        intent = json.loads(raw, object_pairs_hook=unique_object)
        result = query(args.database, intent)
    except Rejected as exc:
        result = exc.payload
    except (ValueError, OSError) as exc:
        result = dict(status='invalid_intent', code='INVALID_INTENT_INPUT', message=str(exc), results=None)
    except sqlite3.Error as exc:
        result = dict(status='data_error', code='DATABASE_ERROR', message=str(exc), results=None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'ok' else 2)


if __name__ == '__main__':
    main()
