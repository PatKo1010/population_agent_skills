"""Synthetic behavioral tests; no production workbook or pipeline artifacts required."""
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('population_query', ROOT / 'scripts/population_query.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'population.sqlite'
        con = sqlite3.connect(self.db)
        con.execute('CREATE TABLE population(year_month,region_name,region_level,sex,age,age_label,population)')
        for month in ['2025-11', '2025-12']:
            for region, level, factor in [('A','local',1),('B','local',1),('C','local',2),('總計','national',4)]:
                for sex, total, child, elderly, centenarian in [('male',40,10,8,1),('female',60,15,12,2)]:
                    for age, label, count in [(None,'all',total),(0,'0',child),(65,'65',elderly),(None,'100+',centenarian)]:
                        con.execute('INSERT INTO population VALUES (?,?,?,?,?,?,?)', (month+'-01',region,level,sex,age,label,count*factor))
        con.commit()
        con.close()
        self.db.with_name('dataset_manifest.json').write_text(json.dumps({'available_months':['2025-11','2025-12'], 'dimensions':['month','region','sex','age'], 'measures':['population']}))

    def run_query(self, operation='population_share', **fields):
        intent = dict(operation=operation, month='2025-12', region_level='local', sex='total')
        intent.update(fields)
        return module.query(self.db, intent)['results']

    def test_female_share_of_all_people(self):
        rows = self.run_query(region='A', sex='female', denominator_sex='total')
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['numerator'],rows[0]['denominator'],rows[0]['percentage']), (60,100,60.0))

    def test_legacy_same_sex_denominator(self):
        row = self.run_query(region='A',sex='female',age_min=65,include_100_plus=True)[0]
        self.assertEqual((row['numerator'],row['denominator'],row['percentage']), (14,60,23.3333))

    def test_age_filtered_cross_sex_share_and_single_age(self):
        row = self.run_query(region='A',sex='female',denominator_sex='total',age_min=65,include_100_plus=True)[0]
        self.assertEqual((row['numerator'],row['denominator']), (14,100))
        self.assertEqual(self.run_query(region='A',age='100+')[0]['numerator'],3)
        self.assertEqual(self.run_query(region='A',age_min=0,age_max=14,include_100_plus=False)[0]['percentage'],25)

    def test_rank_direction_ties_and_legacy_limit(self):
        self.assertEqual([r['region_name'] for r in self.run_query('population_rank',limit=1)],['C'])
        self.assertEqual([r['region_name'] for r in self.run_query('population_rank',order='asc',limit=1,include_ties=True)],['A','B'])
        self.assertEqual(len(self.run_query('population_rank',order='asc',limit=1)),1)
        self.assertEqual(len(self.run_query('population_rank',limit=2,include_ties=True)),3)
        self.assertEqual([r['population'] for r in self.run_query('population_rank',order='asc',limit=1,include_ties=True,age='100+')],[3,3])

    def test_invalid_fields_and_types(self):
        for fields, code in [({'denominator_sex':'male'},'INCOMPATIBLE_DENOMINATOR_SEX'),({'denominator_sex':None},'INVALID_DENOMINATOR_SEX'),({'sort_by':'population'},'UNKNOWN_FIELDS'),({'operation':'population_rank','order':'ASC; DROP TABLE population'},'INVALID_ORDER'),({'operation':'population_rank','include_ties':1},'INVALID_INCLUDE_TIES'),({'operation':'population_rank','limit':True},'INVALID_LIMIT')]:
            intent = dict(operation='population_share',month='2025-12',region_level='local',sex='female')
            intent.update(fields)
            with self.assertRaises(module.Rejected) as ctx:
                module.query(self.db,intent)
            self.assertEqual(ctx.exception.payload['code'],code)
            if code == 'UNKNOWN_FIELDS':
                self.assertIn('denominator_sex',ctx.exception.payload['allowed_fields'])

    def test_region_validation_and_zero_denominator(self):
        for region, code in [('missing','REGION_NOT_AVAILABLE'),('總計','REGION_LEVEL_MISMATCH')]:
            with self.assertRaises(module.Rejected) as ctx:
                self.run_query(region=region)
            self.assertEqual(ctx.exception.payload['code'],code)
        con = sqlite3.connect(self.db)
        con.execute("UPDATE population SET population=0 WHERE region_name='A' AND age_label='all'")
        con.commit()
        con.close()
        with self.assertRaises(module.Rejected) as ctx:
            self.run_query(region='A',age=0)
        self.assertEqual(ctx.exception.payload['code'],'ZERO_DENOMINATOR')

    def test_six_documented_templates_execute(self):
        text = (ROOT/'references/examples.md').read_text()
        intents = [json.loads(block) for block in re.findall(r'```json\n(.*?)\n```', text, re.S)][:6]
        self.assertEqual(len(intents),6)
        for intent in intents:
            result = module.query(self.db,intent)
            self.assertEqual(result['status'],'ok')
            self.assertEqual(result['intent'],intent)
            self.assertTrue(result['results'])

    def test_lookup_and_trend_unchanged(self):
        self.assertEqual(self.run_query('population_lookup',region='A',sex='female')[0]['population'],60)
        intent = dict(operation='population_trend',months=['2025-11','2025-12'],region='A',region_level='local',sex='total')
        self.assertEqual([r['population'] for r in module.query(self.db,intent)['results']],[100,100])


if __name__ == '__main__':
    unittest.main()
