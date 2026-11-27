import itertools
import math
import unittest
from fractions import Fraction as F

from folded_variance import FoldedTest, evaluate, folded, sign_probabilities, wealth


class TestFoldedVariance(unittest.TestCase):
    def test_exact_composite_null(self):
        for m, p in itertools.product(range(2,17), (F(i,20) for i in range(21))):
            for q in (p, 1-p):
                a,b,c = sign_probabilities(m,p,q)
                self.assertEqual(a,b)
                self.assertEqual(a+b+c,1)

    def test_direction_under_independent_arms(self):
        for m,p,q in itertools.product(range(2,13), (F(i,10) for i in range(11)), (F(i,10) for i in range(11))):
            a,b,_ = sign_probabilities(m,p,q)
            d=q*(1-q)-p*(1-p)
            self.assertEqual((a>b)-(a<b),(d>0)-(d<0))

    def test_mixture_martingale_identity(self):
        for n in range(31):
            for w in range(n+1):
                l=n-w
                self.assertEqual((wealth(w+1,l)+wealth(w,l+1))/2,wealth(w,l))

    def test_brute_force_crossing(self):
        alpha=F(1,5)
        schedule=[(F(1,4),F(1,4),F(1,2)), (F(2,5),F(2,5),F(1,5))]*4
        crossed=cost=F(0)
        for path in itertools.product(range(3),repeat=len(schedule)):
            prob=math.prod(schedule[i][v] for i,v in enumerate(path))
            w=l=0
            stop=len(schedule)
            for i,v in enumerate(path,1):
                w+=v==0; l+=v==1
                if wealth(w,l)*alpha>=1:
                    crossed+=prob;stop=i;break
            cost+=stop*prob
        r=evaluate(schedule,alpha)
        self.assertAlmostEqual(r['rejection_probability'],float(crossed),places=13)
        self.assertAlmostEqual(r['expected_tasks'],float(cost),places=13)
        self.assertAlmostEqual(r['mass_check'],1,places=13)

    def test_nonidentical_null(self):
        schedule=[sign_probabilities(m,p,q) for m,p,q in [(8,F(1,20),F(19,20)),(6,F(2,5),F(2,5)),(4,F(1,2),F(1,2)),(3,F(0),F(1))]*20]
        r=evaluate(schedule)
        self.assertLessEqual(r['rejection_probability'],.05)
        self.assertAlmostEqual(r['mass_check'],1)

    def test_ties_and_symmetry(self):
        t=FoldedTest();u=FoldedTest()
        for i,(a,b) in enumerate([(0,4),(1,7),(2,4),(4,0)]*10):
            x=t.update(str(i),a,b,8);y=u.update(str(i),8-b,8-a,8)
            self.assertEqual(x['e'],y['e']);self.assertEqual(x['anytime_p'],y['anytime_p'])
        self.assertEqual(x['ties'],10)

    def test_stopping_and_invalid_update_atomic(self):
        t=FoldedTest();history=[]
        for i in range(30): history.append(t.update(str(i),0,4,8))
        self.assertIsNotNone(t.first_crossing)
        before=len(t.seen)
        for args in [('0',0,1,8),('new',0,9,8),('',0,1,8)]:
            with self.assertRaises(ValueError):t.update(*args)
        self.assertEqual(len(t.seen),before)
        self.assertTrue(all(a['anytime_p']>=b['anytime_p'] for a,b in zip(history,history[1:])))

    def test_invalid_inputs(self):
        for a,m in [(-1,8),(9,8),(0,1),(True,8)]:
            with self.assertRaises(ValueError):folded(a,m)
        for schedule in [[],[(.1,.2,.4)],[(1,0,-1)]]:
            with self.assertRaises(ValueError):evaluate(schedule)
        with self.assertRaises(ValueError):FoldedTest(F(1))

    def test_two_sided_evidence_not_mean_null(self):
        # Equal average variance, unequal per-task variance; no general mean-null claim.
        p=sign_probabilities(2,F(0),F(1,2))
        q=sign_probabilities(8,F(1,2),F(0))
        # Variance differences +1/4 and -1/4 cancel; expected signs do not.
        self.assertEqual(p[0]-p[1]+q[0]-q[1], F(-63,128))


if __name__=='__main__':unittest.main()
