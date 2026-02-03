#!/usr/bin/env python3
"""
Database audit script for Sundial.

Checks for orphaned data and data integrity issues.
Run from project root: python scripts/db_audit.py [--fix]

Options:
  --fix    Automatically fix issues without prompting
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings


async def run_audit(db: AsyncSession) -> dict:
    """Run all audit queries and return results."""
    results = {}

    # 1. Find orphaned tags (tags with no notes)
    orphaned_tags = await db.execute(
        text("""
            SELECT t.id, t.name FROM tags t
            LEFT JOIN note_tags nt ON t.id = nt.tag_id
            WHERE nt.tag_id IS NULL
        """)
    )
    results["orphaned_tags"] = [{"id": row[0], "name": row[1]} for row in orphaned_tags.fetchall()]

    # 2. Find notes with invalid project references
    invalid_project_refs = await db.execute(
        text("""
            SELECT n.id, n.title, n.project_id FROM notes n
            WHERE n.project_id IS NOT NULL
            AND n.project_id NOT IN (SELECT id FROM projects)
        """)
    )
    results["invalid_project_refs"] = [
        {"id": row[0], "title": row[1], "project_id": row[2]}
        for row in invalid_project_refs.fetchall()
    ]

    # 3. Find tasks with invalid project references
    invalid_task_projects = await db.execute(
        text("""
            SELECT t.id, t.title, t.project_id FROM tasks t
            WHERE t.project_id IS NOT NULL
            AND t.project_id NOT IN (SELECT id FROM projects)
        """)
    )
    results["invalid_task_projects"] = [
        {"id": row[0], "title": row[1], "project_id": row[2]}
        for row in invalid_task_projects.fetchall()
    ]

    # 4. Find FTS entries without corresponding notes
    orphaned_fts = await db.execute(
        text("""
            SELECT fts.id, fts.title FROM notes_fts fts
            WHERE fts.id NOT IN (SELECT id FROM notes)
        """)
    )
    results["orphaned_fts"] = [{"id": row[0], "title": row[1]} for row in orphaned_fts.fetchall()]

    # 5. Find notes without FTS entries
    missing_fts = await db.execute(
        text("""
            SELECT n.id, n.title FROM notes n
            WHERE n.id NOT IN (SELECT id FROM notes_fts)
        """)
    )
    results["missing_fts"] = [{"id": row[0], "title": row[1]} for row in missing_fts.fetchall()]

    # 6. Check for duplicate tag names (case sensitivity issues)
    duplicate_tags = await db.execute(
        text("""
            SELECT name, COUNT(*) as cnt FROM tags
            GROUP BY LOWER(name)
            HAVING cnt > 1
        """)
    )
    results["duplicate_tags"] = [{"name": row[0], "count": row[1]} for row in duplicate_tags.fetchall()]

    return results


async def cleanup_orphaned_tags(db: AsyncSession) -> int:
    """Remove orphaned tags. Returns count of deleted tags."""
    result = await db.execute(
        text("""
            DELETE FROM tags WHERE id IN (
                SELECT t.id FROM tags t
                LEFT JOIN note_tags nt ON t.id = nt.tag_id
                WHERE nt.tag_id IS NULL
            )
        """)
    )
    await db.commit()
    return result.rowcount


async def cleanup_orphaned_fts(db: AsyncSession) -> int:
    """Remove orphaned FTS entries. Returns count of deleted entries."""
    result = await db.execute(
        text("""
            DELETE FROM notes_fts WHERE id NOT IN (SELECT id FROM notes)
        """)
    )
    await db.commit()
    return result.rowcount


async def rebuild_missing_fts(db: AsyncSession) -> int:
    """Rebuild FTS entries for notes missing them. Returns count of rebuilt entries."""
    missing = await db.execute(
        text("""
            SELECT n.id, n.title, n.content FROM notes n
            WHERE n.id NOT IN (SELECT id FROM notes_fts)
        """)
    )
    rows = missing.fetchall()

    for row in rows:
        note_id, title, content = row
        # Get tags for this note
        tags_result = await db.execute(
            text("SELECT t.name FROM tags t JOIN note_tags nt ON t.id = nt.tag_id WHERE nt.note_id = :nid"),
            {"nid": note_id},
        )
        tags_str = " ".join(r[0] for r in tags_result.fetchall())

        await db.execute(
            text("INSERT INTO notes_fts(id, title, content, tags) VALUES (:id, :title, :content, :tags)"),
            {"id": note_id, "title": title or "", "content": content or "", "tags": tags_str},
        )

    await db.commit()
    return len(rows)


async def main(auto_fix: bool = False):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("Running database audit...\n")
        results = await run_audit(db)

        has_issues = False

        # Report orphaned tags
        if results["orphaned_tags"]:
            has_issues = True
            print(f"Orphaned tags ({len(results['orphaned_tags'])}):")
            for tag in results["orphaned_tags"]:
                print(f"  - {tag['name']} (id: {tag['id']})")
        else:
            print("Orphaned tags: None")

        # Report invalid project references
        if results["invalid_project_refs"]:
            has_issues = True
            print(f"\nNotes with invalid project refs ({len(results['invalid_project_refs'])}):")
            for note in results["invalid_project_refs"]:
                print(f"  - {note['title']} -> {note['project_id']}")
        else:
            print("Notes with invalid project refs: None")

        if results["invalid_task_projects"]:
            has_issues = True
            print(f"\nTasks with invalid project refs ({len(results['invalid_task_projects'])}):")
            for task in results["invalid_task_projects"]:
                print(f"  - {task['title']} -> {task['project_id']}")
        else:
            print("Tasks with invalid project refs: None")

        # Report FTS issues
        if results["orphaned_fts"]:
            has_issues = True
            print(f"\nOrphaned FTS entries ({len(results['orphaned_fts'])}):")
            for fts in results["orphaned_fts"]:
                print(f"  - {fts['title']} (id: {fts['id']})")
        else:
            print("Orphaned FTS entries: None")

        if results["missing_fts"]:
            has_issues = True
            print(f"\nNotes missing FTS entries ({len(results['missing_fts'])}):")
            for note in results["missing_fts"]:
                print(f"  - {note['title']} (id: {note['id']})")
        else:
            print("Notes missing FTS entries: None")

        # Report duplicate tags
        if results["duplicate_tags"]:
            has_issues = True
            print(f"\nDuplicate tag names ({len(results['duplicate_tags'])}):")
            for tag in results["duplicate_tags"]:
                print(f"  - '{tag['name']}' appears {tag['count']} times")
        else:
            print("Duplicate tag names: None")

        if not has_issues:
            print("\nNo data integrity issues found.")
            return

        # Ask for cleanup
        print("\n" + "=" * 50)
        if not auto_fix:
            try:
                response = input("Run automatic cleanup? [y/N]: ").strip().lower()
                if response != "y":
                    print("Skipping cleanup.")
                    return
            except EOFError:
                print("Non-interactive mode. Use --fix to auto-cleanup.")
                return
        else:
            print("Auto-fix enabled. Running cleanup...")

        # Run cleanups
        if results["orphaned_tags"]:
            count = await cleanup_orphaned_tags(db)
            print(f"Deleted {count} orphaned tags.")

        if results["orphaned_fts"]:
            count = await cleanup_orphaned_fts(db)
            print(f"Deleted {count} orphaned FTS entries.")

        if results["missing_fts"]:
            count = await rebuild_missing_fts(db)
            print(f"Rebuilt {count} missing FTS entries.")

        print("\nCleanup complete. Re-running audit...")
        results = await run_audit(db)
        remaining = sum(len(v) for v in results.values())
        if remaining == 0:
            print("All issues resolved.")
        else:
            print(f"Remaining issues: {remaining}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Sundial database for orphaned data")
    parser.add_argument("--fix", action="store_true", help="Automatically fix issues without prompting")
    args = parser.parse_args()
    asyncio.run(main(auto_fix=args.fix))
