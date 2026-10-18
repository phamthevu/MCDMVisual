import unittest
import numpy as np
from app.core.quant_charts import regression_fit, finite_coefficients, sem_path_layout

class QuantitativeChartStressTests(unittest.TestCase):
    def test_regression_filters_missing_pairs_and_returns_finite_diagnostics(self):
        rng=np.random.default_rng(90210)
        for n in (2,3,10,100,1000):
            x=rng.normal(size=n);y=1.75*x-2+rng.normal(0,.2,size=n)
            if n>4:x[1]=np.nan;y[-1]=np.inf
            result=regression_fit(x,y)
            self.assertEqual(len(result['x']),len(result['residual']))
            self.assertTrue(np.isfinite(result['predicted']).all())
            self.assertTrue(np.isfinite(result['residual']).all())
            self.assertGreaterEqual(result['r2'],0.9 if n>20 else -10)

    def test_regression_rejects_constant_predictor_and_mismatched_input(self):
        with self.assertRaisesRegex(ValueError,'constant'):
            regression_fit([1,1,1],[2,3,4])
        with self.assertRaisesRegex(ValueError,'same number'):
            regression_fit([1,2],[1])
        with self.assertRaisesRegex(ValueError,'two complete'):
            regression_fit([1,np.nan],[2,3])

    def test_sem_paths_keep_only_valid_rows_and_layout_every_node(self):
        rng=np.random.default_rng(91)
        for n in (1,5,30,100):
            names=[f'F{i}' for i in range(n+1)]
            source=[names[i] for i in range(n)];target=[names[i+1] for i in range(n)]
            beta=rng.normal(size=n)
            result=sem_path_layout(source,target,beta)
            self.assertEqual(len(result['edges']),n)
            self.assertEqual(set(result['nodes']),set(result['positions']))
            self.assertTrue(all(np.isfinite(v) for xy in result['positions'].values() for v in xy))
        cycle=sem_path_layout(['A','B','C'],['B','C','A'],[.2,.3,.4])
        self.assertEqual(len(cycle['edges']),3)
        self.assertEqual(set(cycle['positions']),{'A','B','C'})

    def test_coefficients_discard_nonfinite_and_blank_labels(self):
        labels,values=finite_coefficients(['valid','', 'nan-value','another'],[.3,.5,np.nan,-.2])
        self.assertEqual(labels,['valid','another'])
        np.testing.assert_allclose(values,[.3,-.2])

if __name__=='__main__':unittest.main()
