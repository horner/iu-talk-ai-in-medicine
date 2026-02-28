import subprocess
import os

os.chdir("/Volumes/Case/prj/iu-talk/frames")

results = []
for i in range(1, 91):
    fname = f"frame_{i:04d}.jpg"
    r = subprocess.run(["identify", "-verbose", fname], capture_output=True, text=True)
    lines = r.stdout.split("\n")
    for line in lines:
        if "mean:" in line.lower() and "overall" not in line.lower():
            val = line.strip().split()[-1]
            try:
                mean_val = float(val.strip("()"))
            except:
                mean_val = 0
            results.append((fname, mean_val))
            break

results.sort(key=lambda x: -x[1])
print("Top 30 brightest frames:")
for name, val in results[:30]:
    print(f"  {name}: {val:.1f}")
print()
print("Darkest 10 frames:")
for name, val in results[-10:]:
    print(f"  {name}: {val:.1f}")
