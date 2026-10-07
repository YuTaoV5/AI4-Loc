"""Recover only the Kernel Insight supervisor; leave platform models untouched."""
import argparse, json, os, pathlib, signal, subprocess, time

BASE = pathlib.Path('/opt/kernel-insight')
CONFIG = str(BASE/'supervisord.conf')
CTL = [str(BASE/'runtime/venv/bin/supervisorctl'), '-c', CONFIG]

def supervisors():
    found = []
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            args = (entry/'cmdline').read_bytes().split(b'\0')
            if CONFIG.encode() in args and any(pathlib.PurePath(a.decode(errors='replace')).name == 'supervisord' for a in args):
                found.append(int(entry.name))
        except OSError: pass
    return found

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    state = BASE/'data/state.json'
    if state.exists() and any(j.get('status') in ('queued','running') for j in json.loads(state.read_text()).get('jobs',[])):
        raise SystemExit('Active analysis tasks exist; defer service maintenance.')
    processes = supervisors()
    control = subprocess.run(CTL+['pid'], capture_output=True, text=True)
    healthy = control.returncode == 0 and control.stdout.strip().isdigit() and processes == [int(control.stdout.strip())]
    if healthy:
        for command in [['reread'], ['update']] + ([['restart','kernel-insight','ollama-compat']] if args.restart else []):
            subprocess.run(CTL+command, check=True)
    else:
        # All PIDs are verified against the exact project configuration. SIGTERM
        # lets each supervisor stop its own children; never kill model processes.
        for pid in processes:
            if pid in supervisors(): os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic()+40
        while supervisors() and time.monotonic()<deadline: time.sleep(.25)
        if supervisors(): raise SystemExit('Project supervisor did not stop; refusing duplicate launch.')
        sock = BASE/'supervisor.sock'
        if sock.exists(): sock.unlink()
        subprocess.run([str(BASE/'runtime/venv/bin/supervisord'), '-c', CONFIG], check=True)
    subprocess.run(CTL+['status'], check=True)

if __name__ == '__main__': main()
