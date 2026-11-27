import itertools
import math
import unittest
from task_racing import Group, TaskPair, MixtureE, TaskRacing

class TestRacing(unittest.TestCase):
    def test_unbiased_variation(self):
        for g in (2,3,8,16):
            for p in (0,.035,.1,.5,.9,1):
                got=sum(math.comb(g,k)*p**k*(1-p)**(g-k)*Group(k,g,1).variation() for k in range(g+1))
                self.assertAlmostEqual(got,p*(1-p))
    def test_raw_mass(self):
        for g in range(2,12):
            for k in range(g+1):
                m,_=Group(k,g,1).normalized(5)
                self.assertAlmostEqual(m*g,2*k*(g-k)/(g-1))
    def test_cross_product(self):
        types=[((.2,.8),(.4,.4)),((.6,.2),(.2,.9))]
        got=0
        for x,y in itertools.product(types,repeat=2):
            (ma,la),(mb,lb)=x; (na,ka),(nb,kb)=y
            got+=((mb*ka-ma*kb)+(nb*la-na*lb))/8
        self.assertAlmostEqual(got,.3*.5-.4*.65)
    def test_e_exact_small_paths(self):
        for p in (.1,.25,.5,.75,.9):
            prob=0.
            for path in itertools.product((0,1),repeat=10):
                e=MixtureE(alpha=.2,bets=(.5,.95))
                for x in path:e.update(x-p)
                if e.first_crossing:prob+=p**sum(path)*(1-p)**(10-sum(path))
            self.assertLessEqual(prob,.2+1e-12)
    def test_direction_and_stop(self):
        e=MixtureE()
        for _ in range(30):e.update(1.)
        self.assertEqual(e.first_crossing[1],'b_greater')
        hit=e.first_crossing
        for _ in range(100):e.update(-1.)
        self.assertEqual(e.first_crossing,hit)
    def test_group_dependence(self):
        for k in (0,8):self.assertEqual(Group(k,8,10).variation(),0)
    def test_identity_cap_and_block(self):
        r=TaskRacing(8,10)
        p=TaskPair('a',Group(2,8,40),Group(4,8,20))
        self.assertIsNone(r.update(p)['raw_yield'])
        with self.assertRaises(ValueError):r.update(p)
        with self.assertRaises(ValueError):r.update(TaskPair('b',Group(1,8,81),p.b))
        out=r.update(TaskPair('b',p.a,p.b))
        self.assertEqual(out['raw_yield']['n'],1)
        self.assertAlmostEqual(out['rho_raw_per_million'][0],1e6*2*2*6/7/40)
    def test_input(self):
        for x in (float('nan'),float('inf'),-1.1,1.1):
            with self.assertRaises(ValueError):MixtureE().update(x)
        for g,c in ((1,2),(2,0),(True,4)):
            with self.assertRaises(ValueError):TaskRacing(g,c)

if __name__=='__main__':unittest.main()
