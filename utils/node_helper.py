#!/usr/bin/env python3

import os
import signal
import subprocess
import time


def find_process_by_port(port):
    """Find a process using a specific port"""
    try:
        output = subprocess.check_output(
            ["lsof", "-i", f":{port}", "-t"], stderr=subprocess.PIPE, text=True
        ).strip()

        if output:
            return [int(pid) for pid in output.split("\n")]
        return []
    except subprocess.CalledProcessError:
        return []


def kill_process_by_port(port, force=False):
    """Kill processes using a specific port"""
    pids = find_process_by_port(port)

    if not pids:
        return False, "No process found using this port"

    killed = []
    for pid in pids:
        try:
            if force:
                os.kill(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGTERM)
            killed.append(pid)
        except ProcessLookupError:
            pass

    # Check if processes are actually killed
    if not force:
        time.sleep(0.5)  # Give processes time to terminate
        remaining = find_process_by_port(port)
        if remaining:
            # Try force kill if normal termination didn't work
            for pid in remaining:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    return True, f"Killed process(es): {', '.join(map(str, killed))}"


def get_node_service_command(script_path, working_dir=None):
    """Generate proper command for running a Node.js service"""
    # Determine absolute path if working_dir is provided
    if working_dir:
        if not os.path.isabs(script_path):
            script_path = os.path.join(working_dir, script_path)

    # Add signal handling wrapper to ensure proper termination
    cmd = f"exec node {script_path}"

    return cmd
