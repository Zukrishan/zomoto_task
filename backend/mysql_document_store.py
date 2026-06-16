import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiomysql


@dataclass
class UpdateResult:
    modified_count: int


class DocumentCursor:
    def __init__(self, docs: List[Dict[str, Any]], projection: Optional[Dict[str, int]] = None):
        self.docs = docs
        self.projection = projection
        self._limit: Optional[int] = None

    def sort(self, key: str, direction: int):
        reverse = direction == -1
        self.docs.sort(key=lambda d: d.get(key), reverse=reverse)
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    async def to_list(self, length: int):
        cap = self._limit if self._limit is not None else length
        selected = self.docs[:cap]
        return [apply_projection(d, self.projection) for d in selected]


class DocumentCollection:
    def __init__(self, db: "MySQLDocumentDB", name: str):
        self.db = db
        self.name = name

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None):
        docs = await self.db._fetch_collection_docs(self.name)
        for doc in docs:
            if matches_query(doc, query):
                return apply_projection(doc, projection)
        return None

    def find(self, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None):
        async def _run():
            docs = await self.db._fetch_collection_docs(self.name)
            filtered = [d for d in docs if matches_query(d, query)]
            return DocumentCursor(filtered, projection)

        return LazyCursor(_run)

    async def insert_one(self, document: Dict[str, Any]):
        await self.db._insert_doc(self.name, document)

    async def insert_many(self, documents: List[Dict[str, Any]]):
        for doc in documents:
            await self.db._insert_doc(self.name, doc)

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        return await self.db._update_docs(self.name, query, update, many=False)

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        return await self.db._update_docs(self.name, query, update, many=True)

    async def count_documents(self, query: Dict[str, Any]):
        docs = await self.db._fetch_collection_docs(self.name)
        return len([d for d in docs if matches_query(d, query)])


class LazyCursor:
    def __init__(self, factory):
        self._factory = factory
        self._cursor: Optional[DocumentCursor] = None

    async def _ensure(self):
        if self._cursor is None:
            self._cursor = await self._factory()

    def sort(self, key: str, direction: int):
        async def _sort_then_return():
            await self._ensure()
            self._cursor.sort(key, direction)
            return self._cursor

        return LazyCursor(_sort_then_return)

    def limit(self, n: int):
        async def _limit_then_return():
            await self._ensure()
            self._cursor.limit(n)
            return self._cursor

        return LazyCursor(_limit_then_return)

    async def to_list(self, length: int):
        await self._ensure()
        return await self._cursor.to_list(length)


class MySQLDocumentDB:
    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool

    def __getattr__(self, item: str):
        return DocumentCollection(self, item)

    async def close(self):
        self.pool.close()
        await self.pool.wait_closed()

    async def _fetch_collection_docs(self, collection: str):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT data FROM documents WHERE collection_name=%s",
                    (collection,),
                )
                rows = await cur.fetchall()
        return [json.loads(row[0]) for row in rows]

    async def _insert_doc(self, collection: str, document: Dict[str, Any]):
        doc_id = document.get("id")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO documents (collection_name, doc_id, data) VALUES (%s, %s, %s)",
                    (collection, doc_id, json.dumps(document)),
                )
            await conn.commit()

    async def _update_docs(self, collection: str, query: Dict[str, Any], update: Dict[str, Any], many: bool):
        modified = 0
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, data FROM documents WHERE collection_name=%s",
                    (collection,),
                )
                rows = await cur.fetchall()

                for row_id, data in rows:
                    doc = json.loads(data)
                    if not matches_query(doc, query):
                        continue
                    apply_update(doc, update)
                    await cur.execute(
                        "UPDATE documents SET data=%s WHERE id=%s",
                        (json.dumps(doc), row_id),
                    )
                    modified += 1
                    if not many:
                        break
            await conn.commit()
        return UpdateResult(modified_count=modified)


async def create_mysql_document_db(host: str, port: int, user: str, password: str, db_name: str) -> MySQLDocumentDB:
    pool = await aiomysql.create_pool(host=host, port=port, user=user, password=password, db=db_name, autocommit=False)
    db = MySQLDocumentDB(pool)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    collection_name VARCHAR(128) NOT NULL,
                    doc_id VARCHAR(128) NULL,
                    data JSON NOT NULL,
                    UNIQUE KEY uniq_collection_docid (collection_name, doc_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
        await conn.commit()

    return db


def apply_projection(doc: Dict[str, Any], projection: Optional[Dict[str, int]]):
    if not projection:
        return dict(doc)

    result = dict(doc)
    for key, mode in projection.items():
        if mode == 0:
            result.pop(key, None)
    return result


def matches_query(doc: Dict[str, Any], query: Dict[str, Any]):
    for key, condition in query.items():
        value = doc.get(key)
        if isinstance(condition, dict):
            for op, expected in condition.items():
                if op == "$ne" and value == expected:
                    return False
                if op == "$in" and value not in expected:
                    return False
                if op == "$nin" and value in expected:
                    return False
                if op == "$lt" and not (value is not None and value < expected):
                    return False
                if op == "$gte" and not (value is not None and value >= expected):
                    return False
                if op == "$regex":
                    flags = re.IGNORECASE if condition.get("$options", "") == "i" else 0
                    if value is None or re.search(expected, str(value), flags) is None:
                        return False
                if op == "$options":
                    continue
        else:
            if value != condition:
                return False
    return True


def apply_update(doc: Dict[str, Any], update: Dict[str, Any]):
    for op, payload in update.items():
        if op == "$set":
            for k, v in payload.items():
                doc[k] = v
        elif op == "$push":
            for k, v in payload.items():
                arr = doc.get(k)
                if not isinstance(arr, list):
                    arr = []
                arr.append(v)
                doc[k] = arr
