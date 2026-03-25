from __future__ import annotations

import time
from collections import deque

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text


ASCII_BANNER = r"""
 ____ _   _  ___  ___  ___    __  __  ___  ____  __ __  ____  __  ______
||    \\ // // \\ ||\\//||    ||  || // \\ || \\ || || ||    (( \ | || |
||==   )X(  ||=|| || \/ ||    ||==|| ||=|| ||_// \\ // ||==   \\    ||  
||___ // \\ || || ||    ||    ||  || || || || \\  \V/  ||___ \_))   ||  
"""


class HarvesterUI:
    def __init__(self, course_id: str, start_url: str, output_base: str) -> None:
        self.console = Console()
        self.course_id = course_id
        self.start_url = start_url
        self.output_base = output_base

        self.logs: deque[tuple[str, str]] = deque(maxlen=10)

        self.stats = {
            "processed": 0,
            "queued": 0,
            "blacklisted": 0,
            "started": 0,
            "saved": 0,
            "errors": 0,
            "total": 1,
        }

        self.progress = Progress(
            TextColumn("[bold cyan]Scraping course {task.fields[course_id]}"),
            BarColumn(bar_width=None, complete_style="green", finished_style="green"),
            TextColumn("[bold white]{task.percentage:>3.0f}%"),
            TextColumn("[green]{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            TextColumn("[bright_black]{task.fields[rate]}"),
            expand=True,
        )

        self.task_id = self.progress.add_task(
            "crawl",
            total=1,
            completed=0,
            course_id=self.course_id,
            rate="0.00s/page",
        )

        self.live: Live | None = None
        self._last_refresh = 0.0
        self._min_refresh_interval = 0.20

    def start(self) -> None:
        self.live = Live(
            self.render(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
            auto_refresh=False,
        )
        self.live.start()
        self.refresh(force=True)

    def stop(self) -> None:
        self.refresh(force=True)
        if self.live:
            self.live.stop()

    def refresh(self, force: bool = False) -> None:
        if not self.live:
            return

        now = time.monotonic()
        if not force and (now - self._last_refresh) < self._min_refresh_interval:
            return

        self._last_refresh = now
        self.live.update(self.render(), refresh=True)

    def update(
        self,
        *,
        processed: int,
        total: int,
        queued: int,
        blacklisted: int,
        started: int,
        saved: int,
        errors: int,
        rate: str = "",
    ) -> None:
        total = max(total, 1)
        processed = min(processed, total)

        self.stats.update(
            {
                "processed": processed,
                "queued": queued,
                "blacklisted": blacklisted,
                "started": started,
                "saved": saved,
                "errors": errors,
                "total": total,
            }
        )

        self.progress.update(
            self.task_id,
            total=total,
            completed=processed,
            rate=rate or "-",
        )

        self.refresh()

    def info(self, message: str) -> None:
        self._log("INFO", message)

    def warn(self, message: str) -> None:
        self._log("WARN", message)

    def error(self, message: str) -> None:
        self._log("ERROR", message)

    def success(self, message: str) -> None:
        self._log("OK", message)

    def _log(self, level: str, message: str) -> None:
        self.logs.append((level, message))
        self.refresh()

    def render(self):
        banner = Panel(
            Text(ASCII_BANNER.strip("\n"), style="bold magenta"),
            title="Exam Harvester",
            border_style="magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        info_table = Table.grid(expand=True)
        info_table.add_column(style="bold cyan", ratio=1)
        info_table.add_column(style="white", ratio=4)
        info_table.add_row("Course ID", self.course_id)
        info_table.add_row("Start URL", self.start_url)
        info_table.add_row("Output", self.output_base)

        info_panel = Panel(
            info_table,
            title="Session",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )

        stats_table = Table.grid(expand=True)
        stats_table.add_column(justify="left", style="white")
        stats_table.add_column(justify="right", style="bold green")
        stats_table.add_column(justify="left", style="white")
        stats_table.add_column(justify="right", style="bold yellow")

        stats_table.add_row("Processed", str(self.stats["processed"]), "Queued", str(self.stats["queued"]))
        stats_table.add_row("Saved", str(self.stats["saved"]), "Started", str(self.stats["started"]))
        stats_table.add_row("Blacklisted", str(self.stats["blacklisted"]), "Errors", str(self.stats["errors"]))

        stats_panel = Panel(
            stats_table,
            title="Stats",
            border_style="blue",
            box=box.ROUNDED,
            padding=(0, 1),
        )

        progress_panel = Panel(
            self.progress,
            title="Progress",
            border_style="green",
            box=box.ROUNDED,
            padding=(0, 1),
        )

        log_group = []
        if not self.logs:
            log_group.append(Text("No events yet.", style="bright_black"))
        else:
            for level, message in self.logs:
                if level == "INFO":
                    style = "bold cyan"
                elif level == "WARN":
                    style = "bold yellow"
                elif level == "ERROR":
                    style = "bold red"
                elif level == "OK":
                    style = "bold green"
                else:
                    style = "white"

                log_group.append(Text(f"[{level}] {message}", style=style))

        logs_panel = Panel(
            Group(*log_group),
            title="Events",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        body = Group(
            banner,
            info_panel,
            stats_panel,
            progress_panel,
            logs_panel,
        )

        return Panel(
            body,
            title="[bold white]The Exam Harvester CLI[/bold white]",
            border_style="bright_black",
            box=box.ROUNDED,
            padding=(1, 1),
        )