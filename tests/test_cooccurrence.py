import unittest
import numpy as np
import pandas as pd
from app.core.cooccurrence import compute_code_cooccurrence


class CodeCooccurrenceTests(unittest.TestCase):
    def test_wide_presence_counts_shared_excerpts(self):
        data=pd.DataFrame({"Excerpt ID":["E1","E2","E3"],
                           "Trust":[1,0,1],"Process":[1,1,1],"Outcome":[0,1,1]})
        labels,counts,n=compute_code_cooccurrence(data)
        self.assertEqual(labels,["Trust","Process","Outcome"])
        self.assertEqual(n,3)
        np.testing.assert_array_equal(counts,[[2,2,1],[2,3,2],[1,2,2]])
        np.testing.assert_array_equal(counts,counts.T)

    def test_long_assignments_deduplicate_code_per_excerpt(self):
        data=pd.DataFrame({"Excerpt ID":["E1","E1","E1","E2","E2","E3"],
                           "Code":["Trust","Trust","Process","Process","Outcome","Outcome"]})
        labels,counts,n=compute_code_cooccurrence(data)
        self.assertEqual(labels,["Trust","Process","Outcome"])
        self.assertEqual(n,3)
        np.testing.assert_array_equal(counts,[[1,1,0],[1,2,1],[0,1,2]])

    def test_rejects_bad_presence_values_and_single_code(self):
        with self.assertRaisesRegex(ValueError,"0/1"):
            compute_code_cooccurrence(pd.DataFrame({"Excerpt ID":["E1"],"A":[2],"B":[0]}))
        with self.assertRaisesRegex(ValueError,"At least two"):
            compute_code_cooccurrence(pd.DataFrame({"Excerpt ID":["E1","E2"],"Code":["A","A"]}))


if __name__=="__main__":unittest.main()
