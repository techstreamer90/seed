"""
CLI entry point for seed-core.
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Optional
import psutil


def find_spawnie_processes():
    """Find all running spawnie processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('spawnie' in arg.lower() for arg in cmdline):
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cmdline': ' '.join(cmdline) if cmdline else '',
                    'cwd': proc.info.get('cwd', 'N/A')
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes


def find_reality_dirs(root_path: Path = Path.cwd()):
    """Find all directories containing sketch.json files."""
    realities = []
    # Check current directory
    if (root_path / "sketch.json").exists():
        realities.append({
            'path': str(root_path.resolve()),
            'has_model': (root_path / "model").exists()
        })

    # Check parent directories (up to 3 levels)
    current = root_path
    for _ in range(3):
        current = current.parent
        if (current / "sketch.json").exists():
            realities.append({
                'path': str(current.resolve()),
                'has_model': (current / "model").exists()
            })

    # Check immediate subdirectories
    try:
        for item in root_path.iterdir():
            if item.is_dir() and (item / "sketch.json").exists():
                realities.append({
                    'path': str(item.resolve()),
                    'has_model': (item / "model").exists()
                })
    except PermissionError:
        pass

    return realities


def cmd_status(args):
    """Show overall seed ecosystem status."""
    print("=== SEED-CORE STATUS ===\n")

    # Check for spawnie processes
    print("Spawnie Processes:")
    processes = find_spawnie_processes()
    if processes:
        for proc in processes:
            print(f"  PID {proc['pid']}: {proc['name']}")
            print(f"    CWD: {proc['cwd']}")
            print(f"    CMD: {proc['cmdline'][:80]}...")
    else:
        print("  No spawnie processes detected")

    print()

    # Check for realities
    print("Realities:")
    realities = find_reality_dirs()
    if realities:
        for reality in realities:
            model_status = "with model" if reality['has_model'] else "no model"
            print(f"  {reality['path']} ({model_status})")
    else:
        print("  No realities found")

    print(f"\nTotal: {len(processes)} processes, {len(realities)} realities")


def cmd_pulse(args):
    """Check if spawnie is running."""
    processes = find_spawnie_processes()
    if processes:
        print(f"[OK] Spawnie is alive ({len(processes)} process{'es' if len(processes) > 1 else ''})")
        for proc in processes:
            print(f"  PID {proc['pid']}: {proc['name']}")
        sys.exit(0)
    else:
        print("[ERROR] Spawnie is not running")
        sys.exit(1)


def cmd_reality_list(args):
    """List all known realities."""
    realities = find_reality_dirs()
    if not realities:
        print("No realities found")
        return

    for reality in realities:
        path = Path(reality['path'])
        sketch_file = path / "sketch.json"

        # Try to read sketch name
        try:
            with open(sketch_file) as f:
                data = json.load(f)
                name = data.get('name', path.name)
        except Exception:
            name = path.name

        model_status = "[M]" if reality['has_model'] else "[ ]"
        print(f"{model_status} {name}")
        print(f"    {reality['path']}")


def cmd_reality_check(args):
    """Check a specific reality."""
    path = Path(args.path).resolve()

    if not path.exists():
        print(f"[ERROR] Path does not exist: {path}")
        sys.exit(1)

    print(f"=== REALITY CHECK: {path.name} ===\n")

    sketch_file = path / "sketch.json"
    if sketch_file.exists():
        print("[OK] sketch.json found")
        try:
            with open(sketch_file) as f:
                data = json.load(f)
                print(f"  Name: {data.get('name', 'N/A')}")
                print(f"  Version: {data.get('version', 'N/A')}")
        except Exception as e:
            print(f"  Warning: Could not parse sketch.json: {e}")
    else:
        print("[ERROR] sketch.json not found")

    model_dir = path / "model"
    if model_dir.exists():
        print("[OK] model/ directory found")
        try:
            files = list(model_dir.glob("*.json"))
            print(f"  Model files: {len(files)}")
        except Exception:
            print("  Warning: Could not read model directory")
    else:
        print("[ERROR] model/ directory not found")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="seed-core",
        description="Universal process monitoring and reality management"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # status command
    subparsers.add_parser('status', help='Show overall seed ecosystem status')

    # pulse command
    subparsers.add_parser('pulse', help='Check if spawnie is running')

    # reality commands
    reality_parser = subparsers.add_parser('reality', help='Reality management')
    reality_subs = reality_parser.add_subparsers(dest='reality_command')
    reality_subs.add_parser('list', help='List all known realities')
    check_parser = reality_subs.add_parser('check', help='Check a specific reality')
    check_parser.add_argument('path', help='Path to reality directory')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch commands
    if args.command == 'status':
        cmd_status(args)
    elif args.command == 'pulse':
        cmd_pulse(args)
    elif args.command == 'reality':
        if args.reality_command == 'list':
            cmd_reality_list(args)
        elif args.reality_command == 'check':
            cmd_reality_check(args)
        else:
            reality_parser.print_help()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
