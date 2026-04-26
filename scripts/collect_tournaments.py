#!/usr/bin/env python3
"""
collect_tournaments.py – Collect X-Wing tournament data from multiple platforms.

Usage:
    python scripts/collect_tournaments.py [OPTIONS]

Options:
    --days INT          Look back this many days (default: 7, max: 365)
    --platforms LIST    Comma-separated list of platforms to query.
                        Available: longshanks, challonge, bcp, listfortress
                        Default: longshanks,challonge,bcp   (listfortress excluded)
    --output FILE       Path to output JSON file (default: data/tournaments.json)
    --help              Show this help message and exit.

Examples:
    python scripts/collect_tournaments.py --days 30
    python scripts/collect_tournaments.py --days 14 --platforms longshanks,bcp
    python scripts/collect_tournaments.py --days 7 --output /tmp/tournaments.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Platform adapters
# ---------------------------------------------------------------------------

def fetch_longshanks(since: datetime) -> list[dict]:
    """Fetch tournaments from Longshanks (longshanks.org)."""
    try:
        import urllib.request
        import urllib.error

        since_str = since.strftime("%Y-%m-%d")
        url = f"https://longshanks.org/api/events/?game=xwing&from={since_str}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "xwing-miniatures-font/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        events = data if isinstance(data, list) else data.get("events", data.get("results", []))
        results = []
        for ev in events:
            tid = str(ev.get("id") or ev.get("event_id") or "")
            if not tid:
                continue
            results.append({
                "id": f"longshanks-{tid}",
                "platform": "longshanks",
                "name": ev.get("name") or ev.get("title") or "",
                "date": ev.get("date") or ev.get("start_date") or "",
                "players": ev.get("players") or ev.get("player_count") or 0,
                "raw": ev,
            })
        return results
    except Exception as exc:
        print(f"[longshanks] fetch error: {exc}", file=sys.stderr)
        return []


def fetch_challonge(since: datetime) -> list[dict]:
    """Fetch X-Wing tournaments from Challonge public API."""
    api_key = os.environ.get("CHALLONGE_API_KEY", "")
    if not api_key:
        print("[challonge] CHALLONGE_API_KEY not set – skipping.", file=sys.stderr)
        return []
    try:
        import urllib.request
        import urllib.parse

        params = urllib.parse.urlencode({
            "api_key": api_key,
            "created_after": since.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "game_ids": "2088",  # X-Wing on Challonge
        })
        url = f"https://api.challonge.com/v1/tournaments.json?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "xwing-miniatures-font/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        results = []
        for entry in data:
            ev = entry.get("tournament", entry)
            tid = str(ev.get("id") or "")
            if not tid:
                continue
            results.append({
                "id": f"challonge-{tid}",
                "platform": "challonge",
                "name": ev.get("name") or ev.get("url") or "",
                "date": ev.get("started_at") or ev.get("created_at") or "",
                "players": ev.get("participants_count") or 0,
                "raw": ev,
            })
        return results
    except Exception as exc:
        print(f"[challonge] fetch error: {exc}", file=sys.stderr)
        return []


def fetch_bcp(since: datetime) -> list[dict]:
    """Fetch X-Wing tournaments from Best Coast Pairings (BCP)."""
    api_key = os.environ.get("BCP_API_KEY", "")
    if not api_key:
        print("[bcp] BCP_API_KEY not set – skipping.", file=sys.stderr)
        return []
    try:
        import urllib.request
        import urllib.parse

        params = urllib.parse.urlencode({
            "apiKey": api_key,
            "game": "X-Wing",
            "startDate": since.strftime("%Y-%m-%d"),
        })
        url = f"https://www.bestcoastpairings.com/api/events?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "xwing-miniatures-font/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        events = data if isinstance(data, list) else data.get("data", data.get("events", []))
        results = []
        for ev in events:
            tid = str(ev.get("id") or ev.get("eventId") or "")
            if not tid:
                continue
            results.append({
                "id": f"bcp-{tid}",
                "platform": "bcp",
                "name": ev.get("name") or ev.get("eventName") or "",
                "date": ev.get("date") or ev.get("startDate") or "",
                "players": ev.get("playerCount") or ev.get("players") or 0,
                "raw": ev,
            })
        return results
    except Exception as exc:
        print(f"[bcp] fetch error: {exc}", file=sys.stderr)
        return []


def fetch_listfortress(since: datetime) -> list[dict]:
    """Fetch tournaments from ListFortress (opt-in only; generally unmaintained)."""
    try:
        import urllib.request

        url = "https://listfortress.com/api/v1/tournaments"
        req = urllib.request.Request(url, headers={"User-Agent": "xwing-miniatures-font/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        events = data if isinstance(data, list) else data.get("tournaments", [])
        results = []
        for ev in events:
            tid = str(ev.get("id") or "")
            if not tid:
                continue
            date_str = ev.get("date") or ev.get("created_at") or ""
            if date_str:
                try:
                    ev_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if ev_dt.tzinfo is None:
                        ev_dt = ev_dt.replace(tzinfo=timezone.utc)
                    if ev_dt < since:
                        continue
                except ValueError:
                    pass
            results.append({
                "id": f"listfortress-{tid}",
                "platform": "listfortress",
                "name": ev.get("name") or "",
                "date": date_str,
                "players": ev.get("player_count") or 0,
                "raw": ev,
            })
        return results
    except Exception as exc:
        print(f"[listfortress] fetch error: {exc}", file=sys.stderr)
        return []


PLATFORM_FETCHERS = {
    "longshanks": fetch_longshanks,
    "challonge": fetch_challonge,
    "bcp": fetch_bcp,
    "listfortress": fetch_listfortress,
}

DEFAULT_PLATFORMS = ["longshanks", "challonge", "bcp"]


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def load_existing(output_path: Path) -> tuple[list[dict], set[str]]:
    """Load previously-collected records and return (records, id_set)."""
    if not output_path.exists():
        return [], set()
    try:
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    except (json.JSONDecodeError, OSError):
        existing = []
    return existing, {r["id"] for r in existing if "id" in r}


def deduplicate(new_records: list[dict], seen_ids: set[str]) -> tuple[list[dict], int]:
    """Return (unique_new_records, duplicate_count)."""
    unique, dupes = [], 0
    for r in new_records:
        rid = r.get("id")
        if rid in seen_ids:
            dupes += 1
        else:
            seen_ids.add(rid)
            unique.append(r)
    return unique, dupes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Collect X-Wing tournament data from multiple platforms.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        metavar="INT",
        help="Look back this many days (default: 7, max: 365)",
    )
    parser.add_argument(
        "--platforms",
        type=str,
        default=",".join(DEFAULT_PLATFORMS),
        metavar="LIST",
        help=(
            "Comma-separated platforms to query "
            f"(default: {','.join(DEFAULT_PLATFORMS)}). "
            f"Available: {', '.join(PLATFORM_FETCHERS)}"
        ),
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/tournaments.json",
        metavar="FILE",
        help="Output JSON file path (default: data/tournaments.json)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # Validate --days
    if args.days < 1 or args.days > 365:
        print(f"Error: --days must be between 1 and 365, got {args.days}", file=sys.stderr)
        sys.exit(1)

    # Validate platforms
    requested = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    invalid = [p for p in requested if p not in PLATFORM_FETCHERS]
    if invalid:
        print(
            f"Error: unknown platform(s): {', '.join(invalid)}. "
            f"Available: {', '.join(PLATFORM_FETCHERS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    since = datetime.now(tz=timezone.utc) - timedelta(days=args.days)
    output_path = Path(args.output)

    print(f"Collecting tournaments since {since.date()} from: {', '.join(requested)}")

    # Load existing data
    existing, seen_ids = load_existing(output_path)
    print(f"Existing records: {len(existing)} (unique IDs: {len(seen_ids)})")

    # Fetch from each platform
    new_records: list[dict] = []
    for platform in requested:
        print(f"  Fetching from {platform}...", end=" ", flush=True)
        fetched = PLATFORM_FETCHERS[platform](since)
        print(f"{len(fetched)} records")
        new_records.extend(fetched)

    # Deduplicate
    unique_new, dupes = deduplicate(new_records, seen_ids)
    print(f"New unique records: {len(unique_new)} (duplicates skipped: {dupes})")

    # Persist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_records = existing + unique_new
    output_path.write_text(
        json.dumps(all_records, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved {len(all_records)} total records to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
