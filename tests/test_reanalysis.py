import importlib.util
import tempfile
import unittest
from pathlib import Path
import pandas as pd

spec=importlib.util.spec_from_file_location('reanalyse',Path(__file__).resolve().parents[1]/'scripts/reanalyse.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ReanalysisTests(unittest.TestCase):
    def test_input_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'input';p.write_bytes(b'original')
            manifest={'files':{'input':{'path':'input','bytes':8,'sha256':m.digest(p)}}}
            self.assertEqual(m.validate_inputs(root,manifest)['input'],p)
            p.write_bytes(b'modified')
            with self.assertRaises(ValueError):m.validate_inputs(root,manifest)
    def test_comparison_matches_keys_and_detects_change(self):
        old=pd.DataFrame({'id':['a','b'],'estimate':[1.,2.]})
        new=pd.DataFrame({'id':['b','a'],'estimate':[3.,1.+1e-10]})
        result=m.compare_frames(old,new,['id'],1e-8).set_index('id')
        self.assertTrue(result.loc['a','unchanged'])
        self.assertFalse(result.loc['b','unchanged'])
        self.assertEqual(result.loc['b','estimate_delta'],1.)
    def test_missing_numeric_column_rejected(self):
        old=pd.DataFrame({'id':['a'],'estimate':[1.]})
        with self.assertRaises(ValueError):m.compare_frames(old,old[['id']],['id'],1e-8)

    def test_missing_and_duplicate_keys_rejected(self):
        old=pd.DataFrame({'id':['a','b'],'estimate':[1.,2.]})
        with self.assertRaises(ValueError):m.compare_frames(old,old.iloc[:1],['id'],1e-8)
        with self.assertRaises(ValueError):m.compare_frames(old,pd.concat([old,old]),['id'],1e-8)

if __name__=='__main__':unittest.main()
