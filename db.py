"""
数据库连接管理：使用 pymysql + DBUtils.PooledDB 实现连接池
"""
from contextlib import contextmanager

import pymysql
from dbutils.pooled_db import PooledDB

from config import Config

_pool: PooledDB | None = None


def init_pool():
    """初始化连接池（启动时调用一次）"""
    global _pool
    _pool = PooledDB(
        creator=pymysql,
        maxconnections=10,
        mincached=2,
        maxcached=5,
        blocking=True,
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    print(f"[DB] 连接池已初始化 ({Config.DB_USER}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME})")


def close_pool():
    if _pool:
        _pool.close()
        print("[DB] 连接池已关闭")


@contextmanager
def get_conn():
    """从连接池借一条连接，使用完自动归还"""
    if _pool is None:
        init_pool()
    conn = _pool.connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()  # 归还到池


@contextmanager
def get_cursor(commit: bool = False):
    """借 cursor，自动管理 commit/rollback"""
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            yield cur
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
