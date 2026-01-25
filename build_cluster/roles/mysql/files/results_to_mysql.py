import os
import glob
import re
import sys
from typing import Optional, Tuple, List

import pymysql


# ======================
# MySQL config (socket / no password)
# ======================
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = None
MYSQL_DB = "pipeline"

RESULTS_GLOB = "/home/almalinux/results/*_parse.out"
TABLE_NAME = "results"


def to_float(x: Optional[str]) -> Optional[float]:
    if x is None:
        return None
    x = str(x).strip()
    if x == "" or x.lower() == "nan":
        return None
    try:
        return float(x)
    except Exception:
        return None


def norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None


def parse_one_file(
    path: str,
) -> Tuple[
    str,
    Optional[str],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
]:
    """
    Return:
    query_id, best_hit, best_evalue, best_score,
    score_mean, score_std, score_gmean
    """

    query_id = os.path.basename(path).replace("_parse.out", "")
    best_hit = None
    best_evalue = None
    best_score = None
    score_mean = None
    score_std = None
    score_gmean = None

    with open(path, "r", errors="ignore") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # A) CSV / TSV line (preferred)
    for ln in lines:
        if ln.lower().startswith("query_id"):
            continue
        parts = [p.strip() for p in (ln.split(",") if "," in ln else ln.split("\t"))]
        if len(parts) >= 7 and parts[0]:
            return (
                norm(parts[0]),        # query_id
                norm(parts[1]),        # best_hit
                to_float(parts[2]),    # best_evalue
                to_float(parts[3]),    # best_score
                to_float(parts[4]),    # score_mean
                to_float(parts[5]),    # score_std
                to_float(parts[6]),    # score_gmean
            )

    # B) key:value fallback
    kv = {}
    for ln in lines:
        m = re.match(r"^([A-Za-z_ ]+)\s*[:=]\s*(.+)$", ln)
        if m:
            k = m.group(1).strip().lower().replace(" ", "_")
            kv[k] = m.group(2).strip()

    query_id = kv.get("query_id", query_id)
    best_hit = kv.get("best_hit") or kv.get("hit") or kv.get("top_hit")
    best_evalue = kv.get("best_evalue") or kv.get("evalue")
    best_score = kv.get("best_score")
    score_mean = kv.get("score_mean") or kv.get("mean_score") or kv.get("avg_score")
    score_std = kv.get("score_std") or kv.get("std_score")
    score_gmean = kv.get("score_gmean") or kv.get("gmean_score")

    return (
        norm(query_id),
        norm(best_hit),
        to_float(best_evalue),
        to_float(best_score),
        to_float(score_mean),
        to_float(score_std),
        to_float(score_gmean),
    )


def ensure_schema(conn: pymysql.connections.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}`;")
        cur.execute(f"USE `{MYSQL_DB}`;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME}` (
              query_id     VARCHAR(128) NOT NULL,
              best_hit     VARCHAR(255) NULL,
              best_evalue  DOUBLE NULL,
              best_score   DOUBLE NULL,
              score_mean   DOUBLE NULL,
              score_std    DOUBLE NULL,
              score_gmean  DOUBLE NULL,
              PRIMARY KEY (query_id)
            ) ENGINE=InnoDB;
            """
        )
    conn.commit()


def upsert_rows(
    conn: pymysql.connections.Connection,
    rows: List[
        Tuple[
            str,
            Optional[str],
            Optional[float],
            Optional[float],
            Optional[float],
            Optional[float],
            Optional[float],
        ]
    ],
) -> None:
    if not rows:
        return

    sql = f"""
    INSERT INTO `{TABLE_NAME}`
    (query_id, best_hit, best_evalue, best_score, score_mean, score_std, score_gmean)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      best_hit=VALUES(best_hit),
      best_evalue=VALUES(best_evalue),
      best_score=VALUES(best_score),
      score_mean=VALUES(score_mean),
      score_std=VALUES(score_std),
      score_gmean=VALUES(score_gmean);
    """

    with conn.cursor() as cur:
        cur.execute(f"USE `{MYSQL_DB}`;")
        cur.executemany(sql, rows)
    conn.commit()


def main() -> int:
    files = sorted(glob.glob(RESULTS_GLOB))
    if not files:
        print(f"[WARN] No files matched: {RESULTS_GLOB}", file=sys.stderr)
        return 0

    rows = []
    bad = 0

    for p in files:
        try:
            row = parse_one_file(p)
            if not row[0]:
                bad += 1
                continue
            rows.append(row)
        except Exception as e:
            bad += 1
            print(f"[WARN] parse failed: {p}: {e}", file=sys.stderr)

    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=False,
    )

    try:
        ensure_schema(conn)
        upsert_rows(conn, rows)
        with conn.cursor() as cur:
            cur.execute(f"USE `{MYSQL_DB}`;")
            cur.execute(f"SELECT COUNT(*) FROM `{TABLE_NAME}`;")
            total = cur.fetchone()[0]
        print(
            f"[OK] files={len(files)} parsed_rows={len(rows)} "
            f"bad={bad} total_rows_in_db={total}"
        )
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())