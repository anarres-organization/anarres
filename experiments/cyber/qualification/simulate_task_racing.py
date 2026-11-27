"""Synthetic experiments only; no CyberGym data or level-2 claim."""
import json, random
from task_racing import TaskRacing, TaskPair, Group

def run(kind, reps=400, n=300):
    rng=random.Random(20261127+kind)
    nv=ny=0; stops=[]
    for rep in range(reps):
        r=TaskRacing(8,100)
        for t in range(n):
            p=rng.choice((.05,.45))
            a=sum(rng.random()<p for _ in range(8))
            if kind==0:
                b=sum(rng.random()<1-p for _ in range(8)); la=lb=400
            elif kind==1:
                b=sum(rng.random()<p for _ in range(8)); la=720; lb=120
            elif kind==2:
                a=4 if rng.random()<.25 else 0
                b=4 if rng.random()<.5 else 0
                la=200;lb=400
            else:
                a=8*int(rng.random()<p);b=8*int(rng.random()<1-p);la=lb=400
            r.update(TaskPair(str(t),Group(a,8,la),Group(b,8,lb)))
        v=r.variation.first_crossing;y=r.yield_test.first_crossing
        nv+=v is not None;ny+=y is not None
        if y:stops.append(2*y[0])
    return dict(scenario=kind,replicates=reps,max_task_pairs=n,variation_rejections=nv,raw_yield_rejections=ny,mean_yield_stop_if_rejected=sum(stops)/len(stops) if stops else None)
if __name__=='__main__':
    print(json.dumps([run(i) for i in range(4)],indent=2))
