"""Pure data preparation for quantitative charts; no Qt dependency."""
from __future__ import annotations
import numpy as np


def regression_fit(x, y):
    """Return finite OLS fit and residual arrays for visual diagnostics."""
    x=np.asarray(x,dtype=float).reshape(-1);y=np.asarray(y,dtype=float).reshape(-1)
    if x.size!=y.size:raise ValueError("X and Y columns must have the same number of rows.")
    valid=np.isfinite(x)&np.isfinite(y);x=x[valid];y=y[valid]
    if len(x)<2:raise ValueError("At least two complete numeric X/Y rows are required.")
    if np.ptp(x)<=np.finfo(float).eps*max(1.,float(np.max(np.abs(x)))):
        raise ValueError("The predictor column is constant; an OLS slope cannot be estimated.")
    slope,intercept=np.polyfit(x,y,1);pred=slope*x+intercept;res=y-pred
    denom=float(np.sum((y-y.mean())**2));r2=1-float(np.sum(res**2))/denom if denom>0 else float("nan")
    return {"x":x,"y":y,"predicted":pred,"residual":res,"slope":float(slope),"intercept":float(intercept),"r2":r2}


def finite_coefficients(labels, values):
    values=np.asarray(values,dtype=float).reshape(-1);labels=list(labels)
    if len(labels)!=len(values):raise ValueError("Every estimate needs one matching label.")
    valid=[i for i,v in enumerate(values) if np.isfinite(v) and str(labels[i]).strip()]
    return [str(labels[i]) for i in valid],values[valid]


def sem_path_layout(sources, targets, estimates):
    """Validate imported SEM paths and return deterministic layered positions."""
    sources=list(sources);targets=list(targets);values=np.asarray(estimates,dtype=float).reshape(-1)
    if not (len(sources)==len(targets)==len(values)):
        raise ValueError("Source, target, and estimate columns must have the same number of rows.")
    edges=[];nodes=[]
    for source,target,value in zip(sources,targets,values):
        source=str(source).strip();target=str(target).strip()
        if not source or not target or source.lower()=="nan" or target.lower()=="nan" or not np.isfinite(value):continue
        edges.append((source,target,float(value)))
        for node in (source,target):
            if node not in nodes:nodes.append(node)
    if not nodes:return {"nodes":[],"edges":[],"positions":{}}
    # Longest-path layering for acyclic portions; cycles remain at a stable layer.
    depth={node:0 for node in nodes}
    for _ in range(len(nodes)):
        changed=False
        for source,target,_ in edges:
            if source!=target and depth[target]<depth[source]+1:
                depth[target]=depth[source]+1;changed=True
        if not changed:break
    max_depth=max(depth.values()) if depth else 0
    if max_depth >= len(nodes)-1:  # likely a cycle: avoid an unreadable long chain
        depth={node:0 for node in nodes};max_depth=0
    buckets={}
    for node in nodes:buckets.setdefault(depth[node],[]).append(node)
    positions={}
    for layer,items in buckets.items():
        count=len(items)
        for i,node in enumerate(items):
            positions[node]=(float(layer),float((count-1)/2-i))
    return {"nodes":nodes,"edges":edges,"positions":positions}
