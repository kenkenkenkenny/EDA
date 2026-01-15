import csv
import os
import glob
from statistics import mean
import math

Result_Dir = "/home/almalinux/results"
Input_Glob = os.path.join(Result_Dir,"*_parse.out")



Output_Dir = "/home/almalinux/results/output"
os.makedirs(Output_Dir, exist_ok=True)
Hits_Glob = os.path.join(Output_Dir,"hits_output.csv")
Profile_Glob = os.path.join(Output_Dir,"profile_output.csv")


files = glob.glob(Input_Glob)
if not files:
  raise RuntimeError("There are not output files")

def to_float(x):
    try:
        v = float(str(x).strip())
        if math.isnan(v):
            return None
        return v
    except:
        return None

output_query = {}

for path in files:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row["query_id"]
            output_query[qid] = row
  
rows = list(output_query.values())
n = len(rows)

std_vals = []
gmean_vals = []

for r in rows:
    s = to_float(r.get("score_std"))
    g = to_float(r.get("score_gmean"))
    if s is not None:
        std_vals.append(s)
    if g is not None:
        gmean_vals.append(g)

with open(Hits_Glob,"w",newline="") as f:
  writer = csv.writer(f)
  writer.writerow(["fasta_id","best_hit_id"])
  for r in rows:
    writer.writerow([r["query_id"],r["best_hit"]])


with open(Profile_Glob,"w",newline="") as f:
  writer = csv.writer(f)
  writer.writerow(["ave_std","ave_gmean"])
  writer.writerow([mean(std_vals), mean(gmean_vals)])

