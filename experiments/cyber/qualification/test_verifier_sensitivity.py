import itertools
import math
import unittest
from fractions import Fraction as F

from verifier_sensitivity import corrected_difference, sensitivity, _score, fixed_panel_test, BET_FRACTIONS


class SensitivityTest(unittest.TestCase):
    def test_exact_unbiased(self):
        checks = 0
        for m, p, q, (fn, fp) in itertools.product(range(2, 7),
                [F(0), F(1, 10), F(1, 2), F(9, 10), F(1)],
                [F(0), F(1, 10), F(1, 2), F(9, 10), F(1)],
                [(F(0), F(0)), (F(19, 50), F(0)), (F(0), F(1, 10)),
                 (F(1, 5), F(1, 10)), (F(4, 5), F(2, 5))]):
            a, b = [fp + (1-fn-fp)*v for v in (p,q)]
            def pm(k, x):
                return math.comb(m,k)*x**k*(1-x)**(m-k)
            e = sum(pm(i,a)*pm(j,b)*corrected_difference([('t',i,j)],m,fn,fp)
                    for i,j in itertools.product(range(m+1), repeat=2))
            self.assertEqual(e, q*(1-q)-p*(1-p))
            checks += 1
        self.assertEqual(checks,625)

    def test_noiseless_matches_unbiased(self):
        self.assertEqual(corrected_difference([('t',1,2)],8,0,0), F(5,56))

    def test_equal_mirrored_under_channel(self):
        # Population observed variances differ, corrected expectation is zero.
        p,q,fn,fp = F(1,10),F(9,10),F(19,50),F(0)
        a,b = [(1-fn)*x for x in (p,q)]
        self.assertNotEqual(a*(1-a), b*(1-b))
        self.assertEqual(b*(1-b)-a*(1-a)+(fp-fn)*(b-a),0)

    def test_endpoint_linearity(self):
        rows = [('a',1,7),('b',2,4),('c',0,3)]
        def d(h):
            return sum(_score(b,8,h)-_score(a,8,h) for _,a,b in rows)/3
        for h in [F(i,20) for i in range(-20,21)]:
            self.assertEqual(d(h), (1-h)*d(F(-1))/2 + (1+h)*d(F(1))/2)

    def test_wider_interval_cannot_create_certificate(self):
        rows=[(str(i),0,4) for i in range(500)]
        self.assertEqual(sensitivity(rows,8,(0,0))['status'],'B_greater')
        self.assertEqual(sensitivity(rows,8,(-1,1))['status'],'abstain')

    def test_reverse_symmetry(self):
        rows=[(str(i),0,4) for i in range(500)]
        a=sensitivity(rows,8,(-.1,.1))
        b=sensitivity([(t,y,x) for t,x,y in rows],8,(-.1,.1))
        self.assertAlmostEqual(a['numerator_lower'],-b['numerator_upper'])
        self.assertEqual((a['status'],b['status']),('B_greater','A_greater'))

    def test_small_panel_abstains(self):
        self.assertEqual(sensitivity([('a',0,4)],8,(-.1,.1))['status'],'abstain')

    def test_validation(self):
        for rows,m in [([],8),([('a',0,1)],1),([('a',0,1),('a',0,1)],8),
                       ([('a',-1,1)],8),([('a',1,9)],8),([('',1,1)],8)]:
            with self.assertRaises(ValueError): sensitivity(rows,m,(-.1,.1))
        for fn,fp in [(0.5,0.5),(-0.1,0),(0,2)]:
            with self.assertRaises(ValueError): corrected_difference([('a',0,1)],8,fn,fp)
        for h in [(-2,0),(0,2),(.5,-.5)]:
            with self.assertRaises(ValueError): sensitivity([('a',0,1)],8,h)

    def test_heterogeneous_terminal_evalue(self):
        # Independent, not identical: means +1/2, -1/2; average null is zero.
        probs = [F(3,4),F(1,4)]
        for bet in BET_FRACTIONS:
            e=sum(math.prod((p if x==1 else 1-p)*(1+bet*x) for p,x in zip(probs, xs))
                  for xs in itertools.product((-1,1),repeat=2))
            self.assertEqual(e, 1-bet**2/4)
            self.assertLessEqual(e,1)

    def test_e_direction_and_interval(self):
        rows=[(str(i),0,4) for i in range(100)]
        self.assertEqual(fixed_panel_test(rows,8,(0,0))['status'],'B_greater')
        self.assertEqual(fixed_panel_test(rows,8,(-1,1))['status'],'abstain')
        self.assertEqual(fixed_panel_test([(t,b,a) for t,a,b in rows],8,(0,0))['status'],'A_greater')

    def test_e_degenerate_and_validation(self):
        self.assertEqual(fixed_panel_test([('a',1,1)],8,(0,0))['status'],'abstain')
        with self.assertRaises(ValueError): fixed_panel_test([('a',0,1),('a',0,1)],8,(0,0))

if __name__ == '__main__': unittest.main()
