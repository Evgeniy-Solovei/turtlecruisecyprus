from __future__ import annotations

from pathlib import Path


def parse_sql_tuple(sql: str, index: int) -> tuple[list[str], int]:
    index += 1
    fields: list[str] = []
    current: list[str] = []
    in_string = False
    escaped = False
    while index < len(sql):
        char = sql[index]
        if in_string:
            if escaped:
                current.append({"n": "\n", "r": "\r", "t": "\t"}.get(char, char))
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_string = False
            else:
                current.append(char)
        else:
            if char == "'":
                in_string = True
            elif char == ",":
                fields.append("".join(current).strip())
                current = []
            elif char == ")":
                fields.append("".join(current).strip())
                return fields, index + 1
            else:
                current.append(char)
        index += 1
    raise ValueError("Unclosed SQL tuple.")


def iter_insert_rows(sql_path: str | Path, table: str):
    path = Path(sql_path)
    marker = f"INSERT INTO `{table}`"
    statement = ""
    collecting = False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not collecting and marker not in line:
                continue
            collecting = True
            statement += line
            if line.rstrip().endswith(";"):
                values_index = statement.find("VALUES")
                if values_index != -1:
                    index = values_index + len("VALUES")
                    while index < len(statement):
                        while index < len(statement) and statement[index] in " \n\r\t,;":
                            index += 1
                        if index >= len(statement) or statement[index] != "(":
                            break
                        row, index = parse_sql_tuple(statement, index)
                        yield row
                statement = ""
                collecting = False


def load_options(sql_path: str | Path) -> dict[str, str]:
    options: dict[str, str] = {}
    for row in iter_insert_rows(sql_path, "wp_options"):
        if len(row) >= 3:
            options[row[1]] = row[2]
    return options


def load_posts(sql_path: str | Path) -> dict[int, dict]:
    posts: dict[int, dict] = {}
    for row in iter_insert_rows(sql_path, "wp_posts"):
        if len(row) >= 21:
            posts[int(row[0])] = {
                "id": int(row[0]),
                "post_author": row[1],
                "post_date": row[2],
                "post_content": row[4],
                "post_title": row[5],
                "post_status": row[7],
                "post_parent": int(row[17] or 0),
                "post_type": row[20],
            }
    return posts


def load_postmeta(sql_path: str | Path) -> dict[int, dict[str, list[str]]]:
    meta: dict[int, dict[str, list[str]]] = {}
    for row in iter_insert_rows(sql_path, "wp_postmeta"):
        if len(row) >= 4:
            post_id = int(row[1])
            meta.setdefault(post_id, {}).setdefault(row[2], []).append(row[3])
    return meta


def first_meta(meta: dict[int, dict[str, list[str]]], post_id: int, key: str, default: str = "") -> str:
    values = meta.get(post_id, {}).get(key) or []
    return values[0] if values else default


def load_seat_overrides(sql_path: str | Path) -> list[dict]:
    rows = []
    for row in iter_insert_rows(sql_path, "wp_tc_seat_overrides"):
        if len(row) >= 6:
            rows.append(
                {
                    "legacy_id": int(row[0]),
                    "date": row[1],
                    "service_id": int(row[2]),
                    "max_seats": int(row[3] or 0),
                    "is_closed": bool(int(row[4] or 0)),
                    "note": row[5],
                }
            )
    return rows


def load_mpa_customers(sql_path: str | Path) -> list[dict]:
    customers = []
    for row in iter_insert_rows(sql_path, "wp_mpa_customers"):
        if len(row) >= 5:
            customers.append(
                {
                    "id": int(row[0]),
                    "name": row[2],
                    "email": row[3] or "",
                    "phone": row[4] or "",
                }
            )
    return customers
