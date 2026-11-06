"""Penyimpanan proyek di SQLite (file structura.db, atau env STRUCTURA_DB)."""
import datetime
import json
import os
import sqlite3


def _np(o):
    if hasattr(o, "item"): return o.item()
    raise TypeError(type(o))


def _conn():
    c = sqlite3.connect(os.environ.get("STRUCTURA_DB", "structura.db"))
    c.execute("CREATE TABLE IF NOT EXISTS projects(name TEXT PRIMARY KEY, data TEXT NOT NULL, updated TEXT NOT NULL)")
    return c


def save_project(name, model):
    with _conn() as c:
        c.execute("INSERT INTO projects VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                  (name, json.dumps(model, default=_np), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))


def list_projects():
    with _conn() as c:
        return c.execute("SELECT name, updated FROM projects ORDER BY updated DESC").fetchall()


def load_project(name):
    with _conn() as c:
        row = c.execute("SELECT data FROM projects WHERE name=?", (name,)).fetchone()
    if not row: raise KeyError(name)
    return json.loads(row[0])


def delete_project(name):
    with _conn() as c:
        c.execute("DELETE FROM projects WHERE name=?", (name,))
