"""EnvGuard CLI — Protect your environment variables."""

import os
import re
from pathlib import Path
from typing import Dict, Set

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Common patterns for secrets
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey|secret|password|token|auth|credential|private[_-]?key)',
     "Potential secret"),
    (r'[A-Za-z0-9+/]{32,}={0,2}', "Base64-encoded value"),
    (r'sk-[A-Za-z0-9]{32,}', "Stripe/OpenAI-style API key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub personal access token"),
    (r'AKIA[0-9A-Z]{16}', "AWS access key"),
]

COMMON_REQUIRED = [
    "DATABASE_URL", "SECRET_KEY", "API_KEY", "DEBUG",
    "ALLOWED_HOSTS", "CORS_ORIGINS", "LOG_LEVEL",
    "REDIS_URL", "CELERY_BROKER_URL", "SENTRY_DSN",
]


def _load_env(path: str = ".env") -> Dict[str, str]:
    """Load .env file, return dict of variables."""
    env_path = Path(path)
    if not env_path.exists():
        return {}

    vars_dict = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                vars_dict[key] = value
    return vars_dict


def _find_env_files(start: str = ".") -> list:
    """Find all .env files in project."""
    env_files = []
    for root, dirs, files in os.walk(start):
        # Skip node_modules, .git, venv
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__")]
        for f in files:
            if f == ".env" or f.endswith(".env") or f == ".env.example" or f == ".env.local":
                env_files.append(os.path.join(root, f))
    return env_files


@click.group()
@click.version_option(version="1.0.0", prog_name="envguard")
def main():
    """EnvGuard — Validate, generate, and secure your .env files.

    Stop shipping broken configs. One command to check everything.
    """
    pass


@main.command()
@click.option("--path", "-p", default=".", help="Project root to scan")
@click.option("--strict/--lenient", default=False,
              help="Fail (exit 1) on any issue, including warnings")
def check(path, strict):
    """Check .env files for issues.

    Validates syntax, finds missing values, detects hardcoded secrets.
    In --strict mode, any warning or error causes a non-zero exit
    (useful as a CI gate).
    """
    console.print()
    console.print(Panel("[bold]EnvGuard Check[/bold]", border_style="blue"))

    env_files = _find_env_files(path)
    if not env_files:
        console.print("[yellow]No .env files found.[/yellow]")
        return

    console.print(f"Found [bold]{len(env_files)}[/bold] .env file(s)\n")

    total_issues = 0
    worst = 0  # 0 none, 1 info, 2 warning, 3 error

    for env_path in env_files:
        env_vars = _load_env(env_path)
        issues = []

        # Check for empty values
        empty_vars = [k for k, v in env_vars.items() if not v]
        if empty_vars:
            for v in empty_vars:
                issues.append(("warning", f"Empty value: {v}"))

        # Check for placeholder values
        placeholders = ["changeme", "todo", "xxx", "your-", "example", "placeholder"]
        for k, v in env_vars.items():
            if v and any(p in v.lower() for p in placeholders):
                issues.append(("warning", f"Placeholder value: {k}={v[:40]}..."))

        # Check for secrets in plaintext
        for k, v in env_vars.items():
            if not v:
                continue
            for pattern, desc in SECRET_PATTERNS:
                if re.match(pattern, v):
                    issues.append(("error", f"Hardcoded secret: {k} ({desc})"))
                    break

        # Check for common missing variables
        for var in COMMON_REQUIRED:
            if var not in env_vars:
                issues.append(("info", f"Missing common variable: {var}"))

        # Display
        short_path = os.path.relpath(env_path, path) if path != "." else env_path
        if not issues:
            console.print(f"  [green]✓[/green] {short_path} — {len(env_vars)} variables, clean")
        else:
            total_issues += len(issues)
            for severity, msg in issues:
                worst = max(worst, {"info": 1, "warning": 2, "error": 3}[severity])
            console.print(f"  [yellow]{short_path}[/yellow] — {len(env_vars)} variables, {len(issues)} issues:")
            for severity, msg in issues:
                icon = {"error": "[red]✗[/red]", "warning": "[yellow]![/yellow]",
                         "info": "[blue]ℹ[/blue]"}.get(severity, "?")
                console.print(f"    {icon} {msg}")

    console.print()
    if total_issues == 0:
        console.print("[green]All .env files clean.[/green]")
    else:
        console.print(f"[yellow]{total_issues} issue(s) found.[/yellow]")

    if strict and worst >= 2:
        console.print("[red]Strict mode: failing on warnings/errors.[/red]")
        raise SystemExit(1)

@main.command()
@click.option("--path", "-p", default=".env", help="Source .env file")
@click.option("--output", "-o", default=".env.example", help="Output file")
def generate(path, output):
    """Generate .env.example from .env (values removed, keys kept).

    Creates a safe-to-commit template from your .env file.
    """
    console.print()
    console.print(Panel("[bold]EnvGuard Generate[/bold]", border_style="blue"))

    env_vars = _load_env(path)
    if not env_vars:
        console.print(f"[red]No variables found in {path}[/red]")
        return

    lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line.rstrip())
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                lines.append(f"{key}=")
            else:
                lines.append(line.rstrip())

    content = "\n".join(lines) + "\n"
    Path(output).write_text(content, encoding="utf-8")
    console.print(f"[green]✓[/green] Generated {output} with {len(env_vars)} keys (values removed)")


@main.command()
@click.option("--path", "-p", default=".", help="Project root")
def audit(path, strict=False):
    """Full security audit of environment configuration.

    Runs the free security check: detects placeholder secrets, hardcoded
    credentials, missing values, and weak .env hygiene.
    """
    console.print()
    console.print("[bold]EnvGuard security audit[/bold]")
    console.print()
    check(path, strict=strict)


@main.command()
@click.argument("file1")
@click.argument("file2")
def diff(file1, file2):
    """Compare two .env files and show all differences.

    \b
    Example:
        envguard diff .env .env.production
    """
    console.print()
    v1 = _load_env(file1)
    v2 = _load_env(file2)

    all_keys = set(v1.keys()) | set(v2.keys())
    only_in_1 = set(v1.keys()) - set(v2.keys())
    only_in_2 = set(v2.keys()) - set(v1.keys())
    different = {k for k in all_keys if k in v1 and k in v2 and v1[k] != v2[k]}

    console.print(f"[bold]Diff:[/bold] {len(all_keys)} total keys")
    if only_in_1:
        console.print(f"  [yellow]Only in {file1}:[/yellow] {', '.join(sorted(only_in_1))}")
    if only_in_2:
        console.print(f"  [yellow]Only in {file2}:[/yellow] {', '.join(sorted(only_in_2))}")
    if different:
        console.print(f"  [red]Different values:[/red]")
        for k in sorted(different):
            console.print(f"    {k}: {v1[k]!r} -> {v2[k]!r}")
    if not only_in_1 and not only_in_2 and not different:
        console.print("  [green]No differences.[/green]")
    console.print()


if __name__ == "__main__":
    main()
