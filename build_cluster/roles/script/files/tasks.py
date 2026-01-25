from celery import Celery
from Bio import SeqIO
from pathlib import Path
import shutil
import subprocess

app = Celery(
    "worker",
    broker="amqp://admin:abc123@10.134.12.194:5672//",
    backend="rpc://",
)

PYTHON = "/usr/bin/python3.12"
BIG_FASTA = "/home/almalinux/data/uniprot/UP000000589_10090.fasta"
PIPELINE_SCRIPT = Path("/home/almalinux/scripts/pipeline_script.py")
RESULTS_PARSER = Path("/home/almalinux/scripts/results_parser.py")
OUTDIR = Path("/home/almalinux/results")

FASTA_INDEX = None

def get_index():
    global FASTA_INDEX
    if FASTA_INDEX is None:
        FASTA_INDEX = SeqIO.index(BIG_FASTA, "fasta")
    return FASTA_INDEX

@app.task(bind=True, name="pipeline.run_by_id")
def run_pipeline(self, protein_id: str):
    fasta_index = get_index()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    if protein_id not in fasta_index:
        raise ValueError(f"ID {protein_id} not found in FASTA")

    seq = str(fasta_index[protein_id].seq)

    # unique workdir to avoid collisions
    job_id = self.request.id
    workdir = Path("/tmp") / f"job_{protein_id}_{job_id}"
    workdir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(str(PIPELINE_SCRIPT), str(workdir / "pipeline_script.py"))
    shutil.copy2(str(RESULTS_PARSER), str(workdir / "results_parser.py"))

    input_fasta = workdir / "input.fasta"
    input_fasta.write_text(f">{protein_id}\n{seq}\n")

    cmd = [PYTHON, "pipeline_script.py", str(input_fasta)]
    p = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True)

    if p.returncode != 0:
        raise RuntimeError(
            f"Pipeline failed for {protein_id}\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDERR:\n{p.stderr}\n"
            f"STDOUT:\n{p.stdout}\n"
        )

    out_file = workdir / f"{protein_id}_parse.out"
    if not out_file.exists():
        files = ", ".join(sorted([x.name for x in workdir.iterdir()]))
        raise RuntimeError(f"Expected output not found: {out_file}. Workdir has: {files}")

    final = OUTDIR / out_file.name
    shutil.copy2(str(out_file), str(final))

    return {"protein_id": protein_id, "result": str(final), "workdir": str(workdir)}

