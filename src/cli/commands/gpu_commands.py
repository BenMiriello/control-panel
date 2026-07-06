#!/usr/bin/env python3

import json

import click

from core.gpu import get_gpu_overview
from core.gpu.broker import clear_lease, get_lease_state, set_enabled

# Command group metadata
__group__ = "GPU"


def _fmt_mib(mib):
    if mib is None:
        return "?"
    if mib >= 1024:
        return f"{mib / 1024:.1f} GB"
    return f"{mib} MB"


def _print_device(device):
    if not device:
        click.echo("  Device info unavailable")
        return
    used = device.get("mem_used_mib")
    total = device.get("mem_total_mib")
    util = device.get("util_pct")
    temp = device.get("temp_c")
    pct = f"{used / total * 100:.0f}%" if used and total else "?"
    click.echo(f"\n{click.style(device.get('name', 'GPU'), bold=True)}")
    click.echo(
        f"  VRAM: {click.style(_fmt_mib(used), fg='cyan')} / {_fmt_mib(total)} "
        f"({pct})   Util: {util if util is not None else '?'}%   "
        f"Temp: {temp if temp is not None else '?'}°C"
    )


def _print_processes(processes):
    click.echo(f"\n{click.style('On the card:', bold=True)}")
    if not processes:
        click.echo("  Nothing resident")
        return
    for p in processes:
        badge = (
            click.style(f"[{p['managed_by']}]", fg="green")
            if p["managed"]
            else click.style("[unmanaged]", fg="yellow")
        )
        vram = click.style(_fmt_mib(p.get("vram_mib")), fg="cyan")
        cmd = p["command"]
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        click.echo(f"  {vram:>18}  {badge}  PID {p['pid']}  {cmd}")


def _print_broker(state):
    click.echo(f"\n{click.style('Broker lease:', bold=True)}")
    if not state.get("reachable"):
        click.echo("  Redis not reachable — broker state unavailable")
        return
    if not state.get("held"):
        click.echo(f"  {click.style('Idle', fg='green')} (no lease held)")
    else:
        consumer = state.get("consumer") or state.get("kind") or "?"
        priority = state.get("priority") or "?"
        holder = state.get("holder_name") or "?"
        click.echo(
            f"  Held by {click.style(consumer, fg='magenta')} "
            f"(priority: {priority}, caller: {holder})"
        )
        hold = state.get("hold_remaining_s")
        ttl = state.get("ttl_s")
        detail = []
        if hold is not None:
            detail.append(f"fair window {hold}s")
        if ttl is not None:
            detail.append(f"ttl {ttl}s")
        if detail:
            click.echo(f"  {', '.join(detail)}")
    waiters = []
    if state.get("user_pending"):
        waiters.append(f"{state['user_pending']} user")
    if state.get("bg_pending"):
        waiters.append(f"{state['bg_pending']} background")
    if waiters:
        click.echo(f"  Waiting: {', '.join(waiters)}")
    disabled = state.get("disabled") or []
    if disabled:
        click.echo(f"  {click.style('Disabled:', fg='yellow')} {', '.join(disabled)}")


@click.command("gpu")
@click.option("-j", "--json", "json_output", is_flag=True, help="Machine-readable JSON")
def gpu(json_output):
    """Show what is using the GPU and the broker lease state

    Shortcut: g

    Combines the physical truth (nvidia-smi: VRAM + resident processes) with
    the broker's lease view (who holds the card, who is waiting). Works even
    when the coordinating app is down.
    """
    overview = get_gpu_overview()

    if json_output:
        click.echo(json.dumps(overview, indent=2))
        return

    if not overview.get("available"):
        click.secho("No GPU detected (nvidia-smi unavailable)", fg="yellow")
        _print_broker(overview.get("broker", {}))
        return

    _print_device(overview.get("device"))
    _print_processes(overview.get("processes", []))
    _print_broker(overview.get("broker", {}))

    if overview.get("unmanaged_warning"):
        click.echo()
        click.secho(
            "⚠ An unmanaged app is holding significant VRAM — the broker cannot "
            "coordinate or evict it.",
            fg="yellow",
        )
    click.echo()


@click.command("g", hidden=True)
@click.option("-j", "--json", "json_output", is_flag=True)
def g(json_output):
    """Short alias for gpu"""
    gpu.callback(json_output)


@click.command("gpu-clear")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def gpu_clear(yes):
    """Clear a stuck/ghost GPU broker lease

    Force-clears the broker's holder and pending counters (the same operation
    as the broker's own clear-orphans). Use when a crashed worker left a lease
    wedging the card — e.g. after killing a service mid-job.
    """
    state = get_lease_state()
    if not state.get("reachable"):
        click.secho("Redis not reachable — nothing to clear", fg="yellow")
        return

    if not state.get("held"):
        click.secho("No lease is currently held — nothing to clear", fg="green")
        return

    consumer = state.get("consumer") or state.get("kind") or "?"
    holder = state.get("holder_name") or "?"
    click.echo(
        f"Current lease: {click.style(consumer, fg='magenta')} "
        f"(caller: {holder}, priority: {state.get('priority') or '?'})"
    )
    if not yes and not click.confirm("Clear this lease?"):
        click.echo("Aborted")
        return

    if clear_lease():
        click.secho("✓ Lease cleared", fg="green", bold=True)
    else:
        click.secho("✗ Failed to clear lease", fg="red", bold=True)


@click.command("gpu-disable")
@click.argument("consumer")
def gpu_disable(consumer):
    """Block an app from acquiring the GPU (e.g. ollama, comfyui, forge)

    The block is enforced by the shared broker, so it applies to every app on
    the machine, not just Control Panel.
    """
    if set_enabled(consumer, False):
        click.secho(f"✓ '{consumer}' disabled from GPU access", fg="yellow", bold=True)
    else:
        click.secho("✗ Failed (broker Redis unreachable?)", fg="red", bold=True)


@click.command("gpu-enable")
@click.argument("consumer")
def gpu_enable(consumer):
    """Re-enable an app's GPU access"""
    if set_enabled(consumer, True):
        click.secho(f"✓ '{consumer}' re-enabled for GPU access", fg="green", bold=True)
    else:
        click.secho("✗ Failed (broker Redis unreachable?)", fg="red", bold=True)
