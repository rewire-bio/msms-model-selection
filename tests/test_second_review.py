import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'companion'),str(ROOT/'companion/scripts')]
import analyse
from msms_shortlist import cli

class RecallFailures(unittest.TestCase):
    def test_fully_failed_method_remains_in_table(self):
        frame=pd.DataFrame([dict(row=i,pool='official_dedup',b=0.,t=0.) for i in range(3)])
        with patch.object(analyse,'N_BOOT',20):
            metrics,_=analyse.metrics_table({'ok':frame,'failed':frame.iloc[:0]},np.arange(3),np.arange(3))
        failure=metrics[metrics.method=='failed']
        self.assertEqual(len(failure),6)
        self.assertTrue((failure.estimate==0).all())
        self.assertTrue((failure.n_missing_or_failed==3).all())

    def test_invalid_t_and_negative_counts_are_failed(self):
        frame=pd.DataFrame([dict(row=i,pool='official_dedup',b=b,t=t) for i,(b,t) in enumerate([(0.,np.nan),(-1.,0.),(0.,np.inf),(0.,0.)])])
        with patch.object(analyse,'N_BOOT',20):
            metrics,_=analyse.metrics_table({'m':frame},np.arange(4),np.arange(4))
        self.assertTrue((metrics.estimate==25).all())
        self.assertTrue((metrics.n_missing_or_failed==3).all())

class MGFParsing(unittest.TestCase):
    def parse(self,text):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'q.mgf';p.write_text(text);return cli.read_mgf(p)

    def test_bad_peak_does_not_discard_valid_neighbours(self):
        blocks=['BEGIN IONS\nTITLE='+name+'\n'+peak+'\nEND IONS\n' for name,peak in [('before','1 1'),('bad','oops 1'),('after','2 2')]]
        rows=self.parse(''.join(blocks))
        self.assertEqual([r['params']['TITLE'] for r in rows],['before','bad','after'])
        self.assertNotIn('parse_error',rows[0]);self.assertNotIn('parse_error',rows[2])
        table,summary=cli.rank_one(rows[1],None,None,None,None)
        self.assertTrue(table.empty);self.assertEqual(summary['decision'],'refused')

    def test_unterminated_nested_and_orphan_blocks_are_visible(self):
        rows=self.parse('END IONS\nBEGIN IONS\nTITLE=first\n1\nBEGIN IONS\nTITLE=last\n2 2\n')
        self.assertEqual(len(rows),3)
        self.assertTrue(all('parse_error' in row for row in rows))

    def test_no_blocks_is_an_error(self):
        with self.assertRaisesRegex(ValueError,'no spectrum blocks'):
            self.parse('# nothing\n')
