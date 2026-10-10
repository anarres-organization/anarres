#!/usr/bin/env python3
"""Apply the frozen V4 untouched Stage-D environment-level decision rule."""
from __future__ import annotations
import argparse, hashlib, json, math, os
from pathlib import Path
import numpy as np

CELLS=("high_mixed_high_adm","high_mixed_low_adm","low_mixed_high_adm","low_mixed_low_adm")
ORDINARY={"OK","PRED_INCOMPLETE_GENERATION","PRED_PARSE_FAILURE"}
BOOTSTRAPS=100000; BOOT_SEED=2609041501; MIN_USEFUL=.15
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smd(a,b):
    v=.5*(a*(1-a)+b*(1-b)); return 0. if v==0 and a==b else abs(a-b)/math.sqrt(v)
def bootstrap_bounds(values_by_cell,seed=BOOT_SEED,n_boot=BOOTSTRAPS):
    rng=np.random.default_rng(seed); effects=np.empty(n_boot); offset=0
    while offset<n_boot:
        take=min(1000,n_boot-offset); means=[]
        for values in values_by_cell:
            values=np.asarray(values,dtype=float); idx=rng.integers(0,len(values),size=(take,len(values))); means.append(values[idx].mean(axis=1))
        effects[offset:offset+take]=.5*(means[0]+means[2])-.5*(means[1]+means[3]); offset+=take
    return float(np.quantile(effects,.10)),float(np.quantile(effects,.90))
def evaluate(scored_root,manifest):
    result={"schema":"paper1-v4-stage-d-decision-v1","status":"REJECT","rl_launch_permitted":False,"rule":{"bootstrap_resamples":BOOTSTRAPS,"bootstrap_seed":BOOT_SEED,"one_sided_level":.90,"minimum_useful_admissibility_effect":MIN_USEFUL,"promote":"lower_bound > 0.15","reject":"upper_bound < 0.15","inconclusive":"otherwise","mixed_main_effect_min":.30,"success_spread_max":.03,"binary_success_smd_max":.10},"scales":{}}
    decisions=[]
    for scale in ("1p7","4b"):
        cells=[]; cluster_adm=[]; integrity=True; sources=[]
        for cell in CELLS:
            path=Path(scored_root)/scale/f"{cell}.json"; payload=json.loads(path.read_text()); detail=payload["detail"]; groups=payload["groups"]
            by_id={g["example_id"]:[] for g in groups}
            for row in detail:
                if row["example_id"] in by_id: by_id[row["example_id"]].append(row)
            infra=sum(r["verifier_status"] not in ORDINARY for r in detail)
            complete=len(groups)==256 and len(detail)==2048 and len(by_id)==256 and all(len(x)==8 for x in by_id.values()) and infra==0
            integrity &= complete
            adm=[1.-sum(bool(r["truncated"]) for r in rows)/8. for rows in by_id.values()]; cluster_adm.append(adm)
            cells.append({"cell":cell,"success":sum(bool(r["math_correct"]) for r in detail)/2048.,"q_mixed":sum(g["group_type"]=="mixed" for g in groups)/256.,"admissibility":float(np.mean(adm)),"mean_tokens":sum(float(r["num_tokens"]) for r in detail)/2048.,"verifier_infrastructure_errors":infra,"integrity_pass":complete})
            sources.append({"path":str(path),"sha256":sha(path)})
        rates=[c["success"] for c in cells]; qeff=.5*(cells[0]["q_mixed"]+cells[1]["q_mixed"])-.5*(cells[2]["q_mixed"]+cells[3]["q_mixed"]); aeff=.5*(cells[0]["admissibility"]+cells[2]["admissibility"])-.5*(cells[1]["admissibility"]+cells[3]["admissibility"]); gap=max(rates)-min(rates); maxs=max(smd(rates[j],rates[k]) for j in range(4) for k in range(j)); lower,upper=bootstrap_bounds(cluster_adm,BOOT_SEED+(0 if scale=="1p7" else 1))
        balance=integrity and qeff>=.30 and gap<=.03 and maxs<=.10
        if not balance: decision="reject"
        elif lower>MIN_USEFUL: decision="promote"
        elif upper<MIN_USEFUL: decision="reject"
        else: decision="inconclusive"
        decisions.append(decision); result["scales"][scale]={"decision":decision,"integrity_pass":integrity,"balance_pass":balance,"mixed_main_effect":qeff,"admissibility_main_effect":aeff,"admissibility_one_sided_90_bounds":[lower,upper],"max_success_spread":gap,"max_binary_success_smd":maxs,"cells":cells,"sources":sources}
    result["status"]="PROMOTE" if decisions==["promote","promote"] else ("REJECT" if "reject" in decisions else "INCONCLUSIVE")
    result["rl_launch_permitted"]=result["status"]=="PROMOTE"; return result
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--scored-root",type=Path,required=True); ap.add_argument("--manifest",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args(); manifest=json.loads(a.manifest.read_text()); result=evaluate(a.scored_root,manifest); result["manifest"]={"path":str(a.manifest),"sha256":sha(a.manifest)}; a.output.parent.mkdir(parents=True,exist_ok=True); tmp=a.output.with_suffix(a.output.suffix+f".tmp.{os.getpid()}"); tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); tmp.replace(a.output); print(json.dumps({"output":str(a.output),"sha256":sha(a.output),"status":result["status"]},indent=2)); raise SystemExit(0 if result["status"]=="PROMOTE" else 20)
if __name__=="__main__": main()
