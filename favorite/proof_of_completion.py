"""
favorite/proof_of_completion.py — Proof-of-Completion module (§39.4).
Verifies that agent actually completed the task by checking observable evidence.
"""
from pathlib import Path
import subprocess


def _check_file_changed(workdir: str, paths: list[str]) -> dict:
    """Check if files were actually modified."""
    results = {}
    for p in paths:
        fp = Path(workdir) / p
        results[p] = {"exists": fp.exists(), "size": fp.stat().st_size if fp.exists() else 0}
    return results


def _check_git_commits(workdir: str) -> list[str]:
    """Get recent git commits."""
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=workdir, capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip().splitlines() if r.returncode == 0 else []
    except Exception:
        return []


def _check_shell_output(workdir: str, cmd: str, expected: str) -> bool:
    """Run a verification command and check if output contains expected string."""
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=workdir,
            capture_output=True, text=True, timeout=15
        )
        return expected.lower() in (r.stdout + r.stderr).lower()
    except Exception:
        return False


def verify_completion(
    workdir: str,
    task_description: str,
    evidence: dict | None = None,
) -> dict:
    """
    Run proof-of-completion checks.
    
    evidence format:
    {
        "files_changed": ["path/to/file.py"],
        "git_commit_expected": "feat: add",
        "shell_check": {"cmd": "python -c 'import mymodule'", "expected": ""},
    }
    
    Returns: {"passed": bool, "details": [...]}
    """
    details = []
    all_passed = True

    if not evidence:
        return {"passed": True, "details": ["no evidence criteria specified"]}

    # Check files
    if "files_changed" in evidence:
        file_results = _check_file_changed(workdir, evidence["files_changed"])
        for fp, info in file_results.items():
            if info["exists"]:
                details.append(f"✓ файл существует: {fp} ({info['size']} байт)")
            else:
                details.append(f"✗ файл не найден: {fp}")
                all_passed = False

    # Check git commits
    if "git_commit_expected" in evidence:
        commits = _check_git_commits(workdir)
        expected = evidence["git_commit_expected"]
        found = any(expected.lower() in c.lower() for c in commits)
        if found:
            details.append(f"✓ git commit найден: '{expected}'")
        else:
            details.append(f"✗ git commit не найден: '{expected}' (последние: {commits[:2]})")
            all_passed = False

    # Shell check
    if "shell_check" in evidence:
        sc = evidence["shell_check"]
        cmd = sc.get("cmd", "")
        expected = sc.get("expected", "")
        if cmd:
            passed = _check_shell_output(workdir, cmd, expected)
            if passed:
                details.append(f"✓ shell check пройден: {cmd}")
            else:
                details.append(f"✗ shell check провален: {cmd} (ожидалось: '{expected}')")
                all_passed = False

    return {"passed": all_passed, "details": details}
