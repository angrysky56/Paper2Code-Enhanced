#!/usr/bin/env python3
"""
db_query.py — CLI analytics and audit utility for Paper2Code-Enhanced.

Provides clean command line reporting of run history, stage results,
API cost/token details, and debugging convergence rates.
"""

import argparse
import os
import sys
from datetime import datetime

# Add current folder to path to allow robust imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import init_db, Run, StageResult, ExecutionTrial, get_run_summary, get_all_runs, get_session, DB_PATH

try:
    from sqlmodel import select
except ImportError:
    pass

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.align import Align
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

console = Console() if _RICH_AVAILABLE else None


def format_duration(started_at, completed_at):
    if not started_at:
        return "N/A"
    try:
        from datetime import timezone
        if isinstance(started_at, str):
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        else:
            start = started_at

        if not completed_at:
            end = datetime.now(timezone.utc)
        elif isinstance(completed_at, str):
            end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        else:
            end = completed_at

        delta = end - start
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{delta.total_seconds():.1f}s"
    except Exception:
        return "Error"


def format_datetime_str(dt_str: str) -> str:
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str


def show_runs_summary():
    if not os.path.exists(DB_PATH):
        print_error(f"Database file not found at '{DB_PATH}'. Run a pipeline stage first to initialize it.")
        return

    runs = get_all_runs()
    if not runs:
        print_info("No runs found in the database yet.")
        return

    if _RICH_AVAILABLE:
        table = Table(title="📋 Run Execution History", box=box.ROUNDED, expand=True)
        table.add_column("ID", justify="center", style="cyan", no_wrap=True)
        table.add_column("Paper Name", style="bold white")
        table.add_column("Model Used", style="green")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right", style="magenta")
        table.add_column("Tokens (In/Out)", justify="right", style="yellow")
        table.add_column("Cost (USD)", justify="right", style="green")

        for run in runs:
            status_text = Text(run.status.upper())
            if run.status == "completed":
                status_text.stylize("bold green")
            elif run.status == "running":
                status_text.stylize("bold blue")
            else:
                status_text.stylize("bold red")

            duration = format_duration(run.started_at, run.completed_at)
            tokens_in = run.total_tokens_in or 0
            tokens_out = run.total_tokens_out or 0
            cost = run.total_cost or 0.0

            table.add_row(
                str(run.id),
                run.paper_name,
                run.model_used or "N/A",
                status_text,
                duration,
                f"{tokens_in:,} / {tokens_out:,}",
                f"${cost:.4f}",
            )
        console.print(table)
    else:
        print(f"=== Run Execution History ===")
        print(f"{'ID':<4} | {'Paper Name':<25} | {'Model':<20} | {'Status':<10} | {'Duration':<10} | {'Cost':<8}")
        print("-" * 88)
        for run in runs:
            duration = format_duration(run.started_at, run.completed_at)
            cost = run.total_cost or 0.0
            print(f"{run.id:<4} | {run.paper_name:<25} | {run.model_used or 'N/A':<20} | {run.status:<10} | {duration:<10} | ${cost:.4f}")


def show_run_detail(run_id: int):
    if not os.path.exists(DB_PATH):
        print_error(f"Database file not found at '{DB_PATH}'.")
        return

    summary = get_run_summary(run_id)
    if summary.get("status") == "not_found":
        print_error(f"Run ID {run_id} not found in database.")
        return
    elif summary.get("status") == "disabled":
        print_error("Database connection is currently disabled.")
        return

    stages = summary.get("stages", [])
    trials = summary.get("trials", [])

    if _RICH_AVAILABLE:
        # Title and general details panel
        status_text = Text(summary['status'].upper())
        if summary['status'] == "completed":
            status_text.stylize("bold green")
        elif summary['status'] == "running":
            status_text.stylize("bold blue")
        else:
            status_text.stylize("bold red")

        duration = format_duration(summary['started_at'], summary['completed_at'])

        info_text = Text()
        info_text.append(f"Paper Name:    ", style="bold white").append(f"{summary['paper_name']}\n")
        info_text.append(f"Model Used:    ", style="bold white").append(f"{summary['model_used'] or 'N/A'}\n")
        info_text.append(f"Executor:      ", style="bold white").append(f"{summary['executor_type'] or 'N/A'}\n")
        info_text.append(f"Status:        ", style="bold white").append(status_text).append("\n")
        info_text.append(f"Duration:      ", style="bold white").append(f"{duration}\n")
        info_text.append(f"Output Dir:    ", style="bold white").append(f"{summary['output_dir'] or 'N/A'}\n")
        info_text.append(f"Total Cost:    ", style="bold white").append(f"${summary['total_cost']:.5f} USD\n", style="bold green")
        info_text.append(f"Total Tokens:  ", style="bold white").append(f"Input: {summary['total_tokens_in']:,} | Output: {summary['total_tokens_out']:,}\n")

        console.print(Panel(info_text, title=f"🔍 Run Details: Run #{run_id}", border_style="cyan", box=box.ROUNDED))

        # Stages Table
        if stages:
            stage_table = Table(title="📍 Stages Executed", box=box.ROUNDED, expand=True)
            stage_table.add_column("Stage Name", style="bold white")
            stage_table.add_column("Success", justify="center")
            stage_table.add_column("Tokens (In)", justify="right")
            stage_table.add_column("Tokens (Out)", justify="right")
            stage_table.add_column("Cost (USD)", justify="right", style="green")
            stage_table.add_column("Created At", justify="center", style="magenta")

            for s in stages:
                success_mark = "[green]Yes[/green]" if s['success'] else "[red]No[/red]"
                stage_table.add_row(
                    s['stage_name'],
                    success_mark,
                    f"{s['tokens_in']:,}",
                    f"{s['tokens_out']:,}",
                    f"${s['cost_usd']:.5f}",
                    format_datetime_str(s['created_at'])
                )
            console.print(stage_table)
        else:
            print_info("No stages have been logged for this run yet.")

        # Trials Table
        if trials:
            trial_table = Table(title="⚙️ Execution Trials (Debugging Loop)", box=box.ROUNDED, expand=True)
            trial_table.add_column("Trial #", justify="center", style="cyan")
            trial_table.add_column("Success", justify="center")
            trial_table.add_column("Return Code", justify="center")
            trial_table.add_column("Duration", justify="right", style="magenta")
            trial_table.add_column("Timestamp", justify="center")

            for t in trials:
                success_mark = "[green]Yes[/green]" if t['success'] else "[red]No[/red]"
                ret_code = str(t['returncode']) if t['returncode'] is not None else "N/A"
                if t['returncode'] == 0:
                    ret_code = f"[green]{ret_code}[/green]"
                else:
                    ret_code = f"[red]{ret_code}[/red]"

                trial_table.add_row(
                    str(t['attempt_num']),
                    success_mark,
                    ret_code,
                    f"{t['elapsed_seconds']:.2f}s",
                    format_datetime_str(t['created_at'])
                )
            console.print(trial_table)
    else:
        # Standard printed format fallback
        print(f"=== Run Details: Run #{run_id} ===")
        print(f"Paper Name:    {summary['paper_name']}")
        print(f"Model Used:    {summary['model_used'] or 'N/A'}")
        print(f"Status:        {summary['status'].upper()}")
        print(f"Total Cost:    ${summary['total_cost']:.5f} USD")
        print(f"Total Tokens:  Input: {summary['total_tokens_in']:,} | Output: {summary['total_tokens_out']:,}")
        print("-" * 50)
        print("Stages:")
        for s in stages:
            print(f"  - {s['stage_name']}: Success={s['success']}, Cost=${s['cost_usd']:.5f}, Tokens={s['tokens_in']}/{s['tokens_out']}")
        if trials:
            print("Execution Trials:")
            for t in trials:
                print(f"  - Trial {t['attempt_num']}: Success={t['success']}, Returncode={t['returncode']}, Elapsed={t['elapsed_seconds']:.2f}s")


def show_aggregate_stats():
    if not os.path.exists(DB_PATH):
        print_error(f"Database file not found at '{DB_PATH}'.")
        return

    with get_session() as session:
        # Total counts
        total_runs = session.exec(select(Run)).all()
        if not total_runs:
            print_info("No data available to calculate statistics.")
            return

        total_stages = session.exec(select(StageResult)).all()
        total_trials = session.exec(select(ExecutionTrial)).all()

        runs_count = len(total_runs)
        stages_count = len(total_stages)
        trials_count = len(total_trials)

        completed_runs = sum(1 for r in total_runs if r.status == "completed")
        failed_runs = sum(1 for r in total_runs if r.status == "failed")
        running_runs = sum(1 for r in total_runs if r.status == "running")

        total_tokens_in = sum(s.tokens_in for s in total_stages)
        total_tokens_out = sum(s.tokens_out for s in total_stages)
        total_cost = sum(s.cost_usd for s in total_stages)

        # Convergence Rate calculations
        # Group trials by run_id
        trials_by_run = {}
        for t in total_trials:
            trials_by_run.setdefault(t.run_id, []).append(t)

        resolved_runs_trial_counts = []
        for rid, run_trials in trials_by_run.items():
            # If any trial in this run succeeded, how many trials did it take?
            if any(t.success for t in run_trials):
                # The count of trials in this run
                resolved_runs_trial_counts.append(len(run_trials))

        avg_trials_to_converge = (
            sum(resolved_runs_trial_counts) / len(resolved_runs_trial_counts)
            if resolved_runs_trial_counts
            else 0.0
        )

        if _RICH_AVAILABLE:
            stats_text = Text()
            stats_text.append("📊 Total Runs Placed:  ", style="bold white").append(f"{runs_count}\n")
            stats_text.append("   🟢 Completed:      ", style="bold green").append(f"{completed_runs}\n")
            stats_text.append("   🔴 Failed/Interr:  ", style="bold red").append(f"{failed_runs}\n")
            stats_text.append("   🔵 Running:        ", style="bold blue").append(f"{running_runs}\n\n")

            stats_text.append("🪙 Global Resource Footprint:\n", style="bold cyan")
            stats_text.append("   📥 Tokens In:      ", style="bold white").append(f"{total_tokens_in:,}\n")
            stats_text.append("   📤 Tokens Out:     ", style="bold white").append(f"{total_tokens_out:,}\n")
            stats_text.append("   💵 Cumulative Cost:", style="bold white").append(f" ${total_cost:.4f} USD\n\n", style="bold green")

            stats_text.append("🎯 RLM Debugging Loop Performance:\n", style="bold cyan")
            stats_text.append("   ⚙️ Total Trials run: ", style="bold white").append(f"{trials_count}\n")
            stats_text.append("   ✅ Errors resolved:  ", style="bold white").append(f"{len(resolved_runs_trial_counts)}\n")
            stats_text.append("   📈 Debug Convergence Rate: ", style="bold white")
            if avg_trials_to_converge > 0:
                stats_text.append(f"{avg_trials_to_converge:.2f} trials/fix\n", style="bold green")
            else:
                stats_text.append("N/A (No successful repairs logged yet)\n")

            console.print(Panel(stats_text, title="📈 Paper2Code Performance Analytics Dashboard", border_style="green", box=box.ROUNDED))
        else:
            print("=== Paper2Code Performance Analytics Dashboard ===")
            print(f"Total Runs:          {runs_count} (Completed: {completed_runs}, Failed: {failed_runs})")
            print(f"Total Stages:        {stages_count}")
            print(f"Total Trials Logged: {trials_count}")
            print(f"Global Cost:         ${total_cost:.4f} USD")
            print(f"Global Tokens:       Input: {total_tokens_in:,} | Output: {total_tokens_out:,}")
            print(f"Convergence Rate:    {avg_trials_to_converge:.2f} trials/fix")


def get_latest_run_id() -> int:
    if not os.path.exists(DB_PATH):
        return -1
    with get_session() as session:
        statement = select(Run).order_by(Run.id.desc()).limit(1)
        latest = session.exec(statement).first()
        return latest.id if latest else -1


def print_error(msg: str):
    if _RICH_AVAILABLE:
        console.print(f"[bold red]❌ {msg}[/bold red]")
    else:
        print(f"❌ {msg}")


def print_info(msg: str):
    if _RICH_AVAILABLE:
        console.print(f"[bold blue]ℹ️ {msg}[/bold blue]")
    else:
        print(f"ℹ️ {msg}")


def main():
    if os.path.exists(DB_PATH):
        init_db(quiet=True)

    parser = argparse.ArgumentParser(
        description="db_query.py — SQLite Run persistence dashboard & audit tool."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--runs",
        action="store_true",
        help="List all pipeline run records",
    )
    group.add_argument(
        "--run",
        type=int,
        metavar="RUN_ID",
        help="Show detailed trajectory logs and analytics for a specific run ID",
    )
    group.add_argument(
        "--latest",
        action="store_true",
        help="Show detailed trajectory logs for the most recent run",
    )
    group.add_argument(
        "--stats",
        action="store_true",
        help="Show global RLM aggregate statistics, cost footprints, and debugging convergence rates",
    )

    args = parser.parse_args()

    # Default to --runs if no argument provided
    if not (args.runs or args.run is not None or args.latest or args.stats):
        args.runs = True

    if args.runs:
        show_runs_summary()
    elif args.latest:
        latest_id = get_latest_run_id()
        if latest_id == -1:
            print_error("No runs found in the database.")
        else:
            show_run_detail(latest_id)
    elif args.run is not None:
        show_run_detail(args.run)
    elif args.stats:
        show_aggregate_stats()


if __name__ == "__main__":
    main()
