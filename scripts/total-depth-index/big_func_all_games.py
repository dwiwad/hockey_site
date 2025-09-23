import json, time, random, os, math
from pathlib import Path
from typing import List, Dict, Any, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sys import stdout

API_ROOT = "https://api-web.nhle.com/v1/gamecenter"
OUT_DIR = Path("./data/pbp")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_OK = OUT_DIR / "pbp_done_ids.json"     # ids we finished
CHECKPOINT_FAIL = OUT_DIR / "pbp_failed_ids.json" # ids that failed last pass

def load_checkpoint(path: Path) -> set:
    if path.exists():
        with path.open("r") as f:
            try:
                return set(json.load(f))
            except Exception:
                return set()
    return set()

def save_checkpoint(path: Path, items: set):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(sorted(list(items)), f)
    tmp.replace(path)

def make_session() -> requests.Session:
    s = requests.Session()
    # Robust retry policy (handles connection resets, 429, and common 5xx)
    retry = Retry(
        total=8,
        connect=6,
        read=6,
        backoff_factor=1.2,  # exponential backoff
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"GET"},
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": "HockeyDecoded/1.0 (+data pull; contact: you@example.com)"
    })
    return s

def fetch_one_game(session: requests.Session, game_id: int, timeout_s: Tuple[float, float]=(5.0, 20.0)) -> List[Dict[str, Any]]:
    """Returns a list of plays (empty list if none). Raises on non-recoverable errors."""
    url = f"{API_ROOT}/{game_id}/play-by-play"
    resp = session.get(url, timeout=timeout_s)
    # If server returns a known error status, raise_for_status will trigger Retry via adapter only on next calls.
    if resp.status_code >= 400:
        # Let downstream logic decide if we retry manually; still raise to flag the attempt as failed this pass
        resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError as e:
        # Bad JSON; treat as transient
        raise RuntimeError(f"JSON decode error for {game_id}: {e}")

    plays = data.get("plays", [])
    # Add the id to each play
    for p in plays:
        p["game_id"] = game_id
    return plays

def write_ndjson(path: Path, rows: List[Dict[str, Any]]):
    """Append plays to an ndjson per batch for durability."""
    if not rows:
        return
    with path.open("a") as f:
        for r in rows:
            f.write(json.dumps(r))
            f.write("\n")

def backoff_sleep(base: float = 1.5, jitter: float = 0.75):
    # small randomized delay; scale up safely if needed
    time.sleep(base + random.random() * jitter)

def fetch_game_pbp_resumable(game_ids: List[int], batch_size: int = 500, max_passes: int = 3, polite_delay_s: float = 1.3):
    done = load_checkpoint(CHECKPOINT_OK)
    failed_prior = load_checkpoint(CHECKPOINT_FAIL)

    remaining = [gid for gid in game_ids if gid not in done]
    total_games = len(remaining)
    if not remaining:
        print("Nothing to do. All games already fetched.")
        return

    session = make_session()
    out_file = OUT_DIR / "pbp.ndjson"

    for pass_idx in range(1, max_passes + 1):
        print(f"\n=== Pass {pass_idx}/{max_passes} over {len(remaining)} game(s) ===")
        new_done = set()
        new_failed = set()

        for i in range(0, len(remaining), batch_size):
            chunk = remaining[i:i+batch_size]
            batch_rows: List[Dict[str, Any]] = []

            for n, gid in enumerate(chunk, 1):
                # polite rate limit with jitter
                time.sleep(polite_delay_s + random.random() * 0.4)

                # Show live counter (overwrite same line)
                current = total_games - len(remaining) + n
                stdout.write(f"\rFetching game {current}/{total_games} ...")
                stdout.flush()

                try:
                    plays = fetch_one_game(session, gid)
                    batch_rows.extend(plays)
                    new_done.add(gid)
                except requests.HTTPError as e:
                    print(f"\nHTTP error on game {gid}: {e}")
                    new_failed.add(gid)
                    backoff_sleep()
                except (requests.ConnectionError, requests.Timeout) as e:
                    print(f"\nNetwork error on game {gid}: {e}")
                    new_failed.add(gid)
                    backoff_sleep()
                except Exception as e:
                    print(f"\nUnexpected error on game {gid}: {repr(e)}")
                    new_failed.add(gid)
                    backoff_sleep()

            # After each chunk
            write_ndjson(out_file, batch_rows)
            done.update(new_done)
            save_checkpoint(CHECKPOINT_OK, done)
            print(f"\n  Chunk {i//batch_size+1} complete. {len(done)}/{total_games} total games fetched so far.")

        remaining = [gid for gid in remaining if gid not in new_done]

        if not remaining:
            save_checkpoint(CHECKPOINT_FAIL, set())
            print("All requested games fetched successfully.")
            return
        else:
            save_checkpoint(CHECKPOINT_FAIL, set(remaining))
            print(f"Pass {pass_idx} done. {len(remaining)} game(s) still failing; will retry if passes remain.")

    print(f"Finished {max_passes} passes. {len(remaining)} game(s) still failing. See {CHECKPOINT_FAIL}.")

# Assume you already have your list_of_games from earlier
list_of_games = games['id'].tolist()  # make sure it’s a plain list, not a pandas Series

# Run the fetcher
with keep.running():
    fetch_game_pbp_resumable(
        game_ids=list_of_games,
        batch_size=500,      # how many games before flushing to disk
        max_passes=4,        # how many retry passes for stubborn games
        polite_delay_s=1.6   # base delay between requests (add jitter automatically)
    )
    
# Load NDJSON into pandas
df = pd.read_json("~/dev/data/pbp/pbp.ndjson", lines=True)

# Flatten periodDescriptor
pd_flat = pd.json_normalize(df["periodDescriptor"]).add_prefix("period_")

# Flatten details
det_flat = pd.json_normalize(df["details"]).add_prefix("detail_")

# Combine everything
df_flat = pd.concat([df.drop(columns=["periodDescriptor","details"]), pd_flat, det_flat], axis=1)

df_flat.to_csv("~/dev/data/pbp/pbp.csv", index=False)







