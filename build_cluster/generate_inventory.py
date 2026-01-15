#!/usr/bin/env python3

import json
import subprocess
import argparse

def run(command):
    return subprocess.run(command, capture_output=True, encoding='UTF-8')

def generate_inventory():
    command = "terraform output --json host_ips".split()
    host_ip_data = json.loads(run(command).stdout)

    command = "terraform output --json worker_ips".split()
    worker_ip_data = json.loads(run(command).stdout)
    
    host_vars = {}

    counter = 0
    host = []
    workers = []

    for a in host_ip_data:
        name = a
        host_vars[name] = { "ip": [a] }
        host.append(name)
        counter += 1
    
    for a in worker_ip_data:
        name = a
        host_vars[name] = { "ip": [a] }
        workers.append(name)
        counter += 1
    
    
    _meta = {}
    _meta["hostvars"] = host_vars
    _all = { "children": ["workers", "host"] }

    _workers = { "hosts": workers }
    _host = { "hosts": host }

    _jd = {}
    _jd["_meta"] = _meta
    _jd["all"] = _all
    _jd["workers"] = _workers
    _jd["host"] = _host
    
    jd = json.dumps(_jd, indent=4)
    return jd


if __name__ == "__main__":

    ap = argparse.ArgumentParser(
        description = "Generate an inventory from Terraform.",
        prog = __file__
    )

    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list",action="store", nargs="*", default="dummy", help="Show JSON of all managed hosts")
    mo.add_argument("--host",action="store", help="Display vars related to the host")

    args = ap.parse_args()

    if args.host:
        print(json.dumps({}))
    elif len(args.list) >= 0:
        jd = generate_inventory()
        print(jd)
    else:
        raise ValueError("Expecting either --host $HOSTNAME or --list")

    
