#!/usr/bin/env python3
"""Frozen V4 A+B+C four-cell selector; uses no Stage-D or RL outcomes."""
from __future__ import annotations
import argparse, hashlib, json, math, os
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

CELLS=("high_mixed_high_adm","high_mixed_low_adm","low_mixed_high_adm","low_mixed_low_adm")
Q=np.array((1.,1.,-1.,-1.)); A=np.array((1.,-1.,1.,-1.))
NAMESPACE="paper1-v4-ABC-selection-v1"
N_CELL=256
MIN_Q=0.30; MIN_ADM=0.285; MAX_SUCCESS_SPREAD=0.005; MAX_SUCCESS_SMD=0.10; MAX_PROMPT_SMD=0.10

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_jsonl(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def smd(a,b):
    v=.5*(a*(1-a)+b*(1-b)); return 0. if v==0 and a==b else abs(a-b)/math.sqrt(v)
def tie(scale,cell,eid): return int.from_bytes(hashlib.sha256(f"{NAMESPACE}|{scale}|{cell}|{eid}".encode()).digest()[:8],"big")/(2**64-1)
def atomic_jsonl(path, rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+f".tmp.{os.getpid()}")
    with tmp.open("w") as f:
        for row in rows: f.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
        f.flush(); os.fsync(f.fileno())
    tmp.replace(path)

def load_scores(root,stage,scale,expected):
    groups={}; sources=[]
    for shard in range(6):
        path=Path(root)/stage/"scored"/scale/f"shard{shard}.json"; payload=json.loads(path.read_text())
        if int(payload["summary"]["rows"]) != 8*int(payload["summary"]["groups"]): raise ValueError(f"bad summary {path}")
        sources.append({"path":str(path),"sha256":sha(path)})
        for g in payload["groups"]:
            if g["example_id"] in groups: raise ValueError(f"duplicate {stage} identity")
            groups[g["example_id"]]=g
    if set(groups)!=expected: raise ValueError(f"{stage}/{scale} identity mismatch missing={len(expected-set(groups))} extra={len(set(groups)-expected)}")
    return groups,sources

def solve(scale,rows,panel,time_limit):
    n=len(rows); nv=4*n
    p=np.array([r["p_success_abc"] for r in rows]); q=np.array([r["q_mixed_abc"] for r in rows]); adm=np.array([r["p_admissible_abc"] for r in rows])
    chars=np.array([len(panel[r["example_id"]]["prompt"]) for r in rows],dtype=float); char_sd=float(chars.std(ddof=1))
    obj=np.zeros(nv)
    for j,cell in enumerate(CELLS): obj[j*n:(j+1)*n]=-(Q[j]*q+A[j]*adm)+1e-9*np.array([tie(scale,cell,r["example_id"]) for r in rows])
    cons=[]
    def add(e,lo,hi): cons.append((e,lo,hi))
    for j in range(4): add([(j*n+i,1.) for i in range(n)],N_CELL,N_CELL)
    for i in range(n): add([(j*n+i,1.) for j in range(4)],0.,1.)
    for j in range(4):
        for k in range(j):
            add([(j*n+i,p[i]) for i in range(n)]+[(k*n+i,-p[i]) for i in range(n)],-MAX_SUCCESS_SPREAD*N_CELL,MAX_SUCCESS_SPREAD*N_CELL)
            add([(j*n+i,chars[i]) for i in range(n)]+[(k*n+i,-chars[i]) for i in range(n)],-MAX_PROMPT_SMD*char_sd*N_CELL,MAX_PROMPT_SMD*char_sd*N_CELL)
    for j,k,v in ((0,1,q),(2,3,q),(0,2,adm),(1,3,adm)):
        add([(j*n+i,v[i]) for i in range(n)]+[(k*n+i,-v[i]) for i in range(n)],-.05*N_CELL,.05*N_CELL)
    for field in ("source","problem_type"):
        for level in sorted({str(panel[r["example_id"]].get(field,"")) for r in rows}):
            ind=np.array([float(str(panel[r["example_id"]].get(field,""))==level) for r in rows])
            if ind.sum()<4: continue
            for j in range(1,4): add([(j*n+i,ind[i]) for i in range(n)]+[(i,-ind[i]) for i in range(n)],-.05*N_CELL,.05*N_CELL)
    # Prospective factor-separation constraints.
    add([(j*n+i,Q[j]*q[i]) for j in range(4) for i in range(n)],2*N_CELL*MIN_Q,np.inf)
    add([(j*n+i,A[j]*adm[i]) for j in range(4) for i in range(n)],2*N_CELL*MIN_ADM,np.inf)
    mat=lil_matrix((len(cons),nv)); lo=np.empty(len(cons)); hi=np.empty(len(cons))
    for r,(entries,a,b) in enumerate(cons):
        for col,val in entries: mat[r,col]=val
        lo[r]=a; hi[r]=b
    result=milp(c=obj,integrality=np.ones(nv),bounds=Bounds(np.zeros(nv),np.ones(nv)),constraints=LinearConstraint(mat.tocsr(),lo,hi),options={"time_limit":time_limit,"mip_rel_gap":.001})
    if result.x is None: raise RuntimeError(f"V4 selector infeasible status={result.status} {result.message}")
    chosen=[np.flatnonzero(result.x[j*n:(j+1)*n]>.5).tolist() for j in range(4)]
    cells=[]
    for cell,ix in zip(CELLS,chosen):
        cells.append({"cell":cell,"n":len(ix),"success_abc":float(p[ix].mean()),"q_mixed_abc":float(q[ix].mean()),"admissibility_abc":float(adm[ix].mean()),"mean_tokens_abc":float(np.mean([rows[i]["mean_tokens_abc"] for i in ix])),"mean_prompt_chars":float(chars[ix].mean()),"source_counts":dict(sorted(Counter(panel[rows[i]["example_id"]].get("source","") for i in ix).items())),"problem_type_counts":dict(sorted(Counter(panel[rows[i]["example_id"]].get("problem_type","") for i in ix).items()))})
    rates=[x["success_abc"] for x in cells]
    prompt_spread=max(x["mean_prompt_chars"] for x in cells)-min(x["mean_prompt_chars"] for x in cells)
    prompt_smd=0. if char_sd==0. and prompt_spread==0. else prompt_spread/char_sd
    audit={"solver_status":int(result.status),"solver_message":result.message,"cells":cells,"mixed_main_effect":.5*(cells[0]["q_mixed_abc"]+cells[1]["q_mixed_abc"])-.5*(cells[2]["q_mixed_abc"]+cells[3]["q_mixed_abc"]),"admissibility_main_effect":.5*(cells[0]["admissibility_abc"]+cells[2]["admissibility_abc"])-.5*(cells[1]["admissibility_abc"]+cells[3]["admissibility_abc"]),"max_success_spread":max(rates)-min(rates),"max_binary_success_smd":max(smd(rates[j],rates[k]) for j in range(4) for k in range(j)),"max_prompt_length_smd":prompt_smd}
    audit["selection_gate_pass"]=(audit["mixed_main_effect"]>=MIN_Q-1e-12 and audit["admissibility_main_effect"]>=MIN_ADM-1e-12 and audit["max_success_spread"]<=MAX_SUCCESS_SPREAD+1e-12 and audit["max_binary_success_smd"]<=MAX_SUCCESS_SMD+1e-12 and audit["max_prompt_length_smd"]<=MAX_PROMPT_SMD+1e-12 and len(set().union(*(set(x) for x in chosen)))==4*N_CELL)
    if not audit["selection_gate_pass"]: raise RuntimeError("V4 post-solve gate failed")
    return audit,chosen

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--package",type=Path,required=True); ap.add_argument("--output-root",type=Path,required=True); ap.add_argument("--time-limit",type=float,default=1800.); a=ap.parse_args()
    panel_rows=load_jsonl(a.package/"stage0/openr1_v4_stage0_panel_6000.jsonl"); panel={r["example_id"]:r for r in panel_rows}
    result={"schema":"paper1-v4-abc-selection-v1","status":"FROZEN_SELECTOR_RESULT","uses_stage_d_or_rl_outcomes":False,"selection_namespace":NAMESPACE,"thresholds":{"n_cell":N_CELL,"mixed_main_effect_min":MIN_Q,"admissibility_main_effect_min":MIN_ADM,"success_spread_max":MAX_SUCCESS_SPREAD,"binary_success_smd_max":MAX_SUCCESS_SMD,"prompt_length_smd_max":MAX_PROMPT_SMD},"scales":{}}
    for scale in ("1p7","4b"):
        ids={r["example_id"] for r in load_jsonl(a.package/f"stage_a/shortlist/{scale}_stage_b_unique_union.jsonl")}
        A0,sa=load_scores(a.package,"stage_a",scale,set(panel)); B,sb=load_scores(a.package,"stage_b",scale,ids); C,sc=load_scores(a.package,"stage_c",scale,ids)
        rows=[]
        for eid in sorted(ids):
            gs=[A0[eid],B[eid],C[eid]]; successes=sum(int(g["successes"]) for g in gs)
            rows.append({"example_id":eid,"p_success_abc":successes/24.,"q_mixed_abc":sum(g["group_type"]=="mixed" for g in gs)/3.,"p_admissible_abc":1.-sum(float(g["truncation_rate"]) for g in gs)/3.,"mean_tokens_abc":sum(float(g["mean_tokens"]) for g in gs)/3.})
        audit,chosen=solve(scale,rows,panel,a.time_limit); files={}
        for cell,ix in zip(CELLS,chosen):
            out=a.output_root/f"{scale}_{cell}_stage_d_panel.jsonl"; values=[]
            for i in sorted(ix,key=lambda i:rows[i]["example_id"]):
                row=dict(panel[rows[i]["example_id"]]); row["v4_abc_selection"]=rows[i]; values.append(row)
            atomic_jsonl(out,values); files[cell]={"path":str(out),"rows":N_CELL,"sha256":sha(out)}
        result["scales"][scale]={"audit":audit,"sources":{"A":sa,"B":sb,"C":sc},"selected_files":files}
    a.output_root.mkdir(parents=True,exist_ok=True); out=a.output_root/"abc_selection_audit.json"; tmp=out.with_suffix(".json.tmp"); tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); tmp.replace(out); print(out); print(sha(out))
if __name__=="__main__": main()
