from __future__ import annotations

import asyncio
import sys


def print_usage() -> None:
    print("Usage:")
    print("  python -m app.main login")
    print("  python -m app.main sync [course_id_or_exams_url]")
    print("  python -m app.main build-index [course_id_or_exams_url]")
    print("  python -m app.main export-pending [course_id_or_exams_url]")


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].strip().lower()
    course_ref = sys.argv[2].strip() if len(sys.argv) >= 3 else None

    if command == "login":
        from app.login import run_login
        run_login()
    elif command == "sync":
        from app.crawler import run_crawler
        asyncio.run(run_crawler(course_ref))
    elif command == "build-index":
        from app.build_index import build_index
        build_index(course_ref)
    elif command == "export-pending":
        from app.export_pending_questions import main as export_pending_main
        export_pending_main(course_ref)
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()