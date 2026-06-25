"""Characterize each named sub-body of the SHTF20S3M100-5 idler assembly."""
import numpy as np, trimesh, json

GLB = "cad/SHTF20S3M100-5.glb"
scene = trimesh.load(GLB, force="scene")

def analyze(name, g):
    V = g.vertices * 1000.0
    xmin,xmax = V[:,0].min(), V[:,0].max()
    ymin,ymax = V[:,1].min(), V[:,1].max()
    zmin,zmax = V[:,2].min(), V[:,2].max()
    # bore axis assumed = X (per part frame). radius from (y,z)=(0,0)
    r = np.sqrt(V[:,1]**2 + V[:,2]**2)
    print(f"\n=== {name} ===")
    print(f"  X[{xmin:.2f},{xmax:.2f}] len={xmax-xmin:.2f}  "
          f"Y[{ymin:.2f},{ymax:.2f}]  Z[{zmin:.2f},{zmax:.2f}]  tris={len(g.faces)}")
    # distinct radius bands via histogram over ALL vertices of this body
    hist, edges = np.histogram(r, bins=600, range=(0, 13))
    thr = max(20, hist.max()*0.04)
    peaks=[]
    for i in range(2, len(hist)-2):
        if hist[i] > thr and hist[i] >= hist[i-1] and hist[i] > hist[i+1]:
            peaks.append(round(0.5*(edges[i]+edges[i+1]),2))
    dedup=[peaks[0]] if peaks else []
    for p in peaks[1:]:
        if abs(p-dedup[-1])>0.25: dedup.append(p)
    print(f"  radial vertex-density peaks (O values): {dedup}")

for name, g in scene.geometry.items():
    analyze(name, g)

# Now: where along X does the O5 bore exist? Project: for thin X-slices of the
# COMBINED mesh, count vertices near r=2.5 (O5) vs r=5.5 (bearing OD) vs r=9 (drum).
print("\n\n=== axial occupancy: which features exist at each X ===")
mesh = trimesh.util.concatenate(list(scene.geometry.values()))
V = mesh.vertices * 1000.0
r = np.sqrt(V[:,1]**2 + V[:,2]**2)
print(f"  {'x':>6} {'O5 vtx':>7} {'O5.5':>6} {'O9':>6} {'O11':>6} {'total':>7}")
for x0 in np.arange(-7, 16, 0.5):
    m = (V[:,0] >= x0) & (V[:,0] < x0+0.5)
    if m.sum() < 30:
        continue
    rr = r[m]
    n5 = ((rr>2.2)&(rr<2.8)).sum()
    n55= ((rr>5.2)&(rr<5.8)).sum()
    n9 = ((rr>8.5)&(rr<9.7)).sum()
    n11= ((rr>10.6)&(rr<11.3)).sum()
    print(f"  {x0:6.1f} {n5:7d} {n55:6d} {n9:6d} {n11:6d} {int(m.sum()):7d}")
