import subprocess, tempfile, os

def ngspice(net):
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
        f.write(net); p = f.name
    r = subprocess.run(["ngspice", "-b", p], capture_output=True, text=True)
    os.unlink(p)
    return r.stdout + r.stderr
