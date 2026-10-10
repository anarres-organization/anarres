#!/usr/bin/env python3
"""Apply the frozen V4 Stage-D gate to 14B."""
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
CELLS=("high_mixed_high_adm","high_mixed_low_adm","low_mixed_high_adm","low_mixed_low_adm"); ORDINARY={"OK","PRED_INCOMPLETE_GENERATION","PRED_PARSE_FAILURE"}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smd(a,b):
 v=.5*(a*(1-a)+b*(1-b)); return 0 if v==0 and a==b else abs(a-b)/math.sqrt(v)
def bounds(values,n=100000,seed=2609071501):
 rng=np.random.default_rng(seed); out=np.empty(n); off=0
 while off<n:
  take=min(1000,n-off); means=[]
  for v in values: v=np.asarray(v,float); means.append(v[rng.integers(0,len(v),size=(take,len(v)))].mean(1))
  out[off:off+take]=.5*(means[0]+means[2])-.5*(means[1]+means[3]); off+=take
 return [float(np.quantile(out,.10)),float(np.quantile(out,.90))]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--scored-root",type=Path,required=True); ap.add_argument("--manifest",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args(); cells=[]; av=[]; integrity=True
 for cell in CELLS:
  p=a.scored_root/f"{cell}.json"; d=json.loads(p.read_text()); by={g["example_id"]:[] for g in d["groups"]}
  for r in d["detail"]:
   if r["example_id"] in by: by[r["example_id"]].append(r)
  infra=sum(r["verifier_status"] not in ORDINARY for r in d["detail"]); ok=len(d["groups"])==256 and len(d["detail"])==2048 and all(len(x)==8 for x in by.values()) and infra==0; integrity &= ok
  adm=[1-sum(bool(r["truncated"]) for r in rr)/8 for rr in by.values()]; av.append(adm)
  cells.append({"cell":cell,"success":sum(bool(r["math_correct"]) for r in d["detail"])/2048,"q_mixed":sum(g["group_type"]=="mixed" for g in d["groups"])/256,"admissibility":float(np.mean(adm)),"mean_tokens":sum(r["num_tokens"] for r in d["detail"])/2048,"integrity_pass":ok,"verifier_infrastructure_errors":infra,"source":{"path":str(p),"sha256":sha(p)}})
 rates=[x["success"] for x in cells]; q=.5*(cells[0]["q_mixed"]+cells[1]["q_mixed"])-.5*(cells[2]["q_mixed"]+cells[3]["q_mixed"]); ae=.5*(cells[0]["admissibility"]+cells[2]["admissibility"])-.5*(cells[1]["admissibility"]+cells[3]["admissibility"]); gap=max(rates)-min(rates); ms=max(smd(rates[j],rates[k]) for j in range(4) for k in range(j)); lo,hi=bounds(av)
 balance=integrity and q>=.30 and gap<=.03 and ms<=.10; decision="promote" if balance and lo>.15 else ("reject" if not balance or hi<.15 else "inconclusive")
 out={"schema":"paper1-v4-14b-stage-d-decision-v1","status":decision.upper(),"rl_launch_permitted":decision=="promote","integrity_pass":integrity,"balance_pass":balance,"mixed_main_effect":q,"admissibility_main_effect":ae,"admissibility_one_sided_90_bounds":[lo,hi],"max_success_spread":gap,"max_binary_success_smd":ms,"cells":cells,"manifest":{"path":str(a.manifest),"sha256":sha(a.manifest)}}
 a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps(out,indent=2)); raise SystemExit(0 if decision=="promote" else 20)
if __name__=="__main__": main()
