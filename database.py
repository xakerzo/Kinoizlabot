import aiosqlite
import os
from datetime import datetime
from config import DATABASE_URL, DB_NAME

class Database:
    def __init__(self):
        self.db_path = DB_NAME

    async def _connect(self):
        # In a real scenario with PostgreSQL, you'd use asyncpg here.
        # For now, following the pattern provided.
        return await aiosqlite.connect(self.db_path)

    async def create_transaction(self, user_id, amount):
        async with await self._connect() as db:
            await db.execute(
                "INSERT INTO transactions(user_id, amount, status, created_at) VALUES (?, ?, 'pending', ?)",
                (user_id, amount, datetime.utcnow().isoformat())
            )
            await db.commit()
            cursor = await db.execute("SELECT id FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
            row = await cursor.fetchone()
            return row[0]

    async def get_transaction(self, t_id):
        async with await self._connect() as db:
            cursor = await db.execute("SELECT user_id, amount, status FROM transactions WHERE id=?", (t_id,))
            return await cursor.fetchone()

    async def get_transaction_payme_id(self, t_id):
        async with await self._connect() as db:
            cursor = await db.execute("SELECT payme_id FROM transactions WHERE id=?", (t_id,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def update_transaction_status(self, t_id, status):
        async with await self._connect() as db:
            await db.execute("UPDATE transactions SET status=? WHERE id=?", (status, t_id))
            await db.commit()

    async def update_transaction_payme_id(self, t_id, payme_id):
        async with await self._connect() as db:
            await db.execute("UPDATE transactions SET payme_id=? WHERE id=?", (payme_id, t_id))
            await db.commit()

    async def get_transaction_by_payme_id(self, payme_id):
        async with await self._connect() as db:
            cursor = await db.execute("SELECT id, user_id, amount, status, created_at FROM transactions WHERE payme_id=?", (payme_id,))
            return await cursor.fetchone()

    async def get_transactions_by_time_range(self, from_ms, to_ms):
        async with await self._connect() as db:
            cursor = await db.execute(
                "SELECT id, user_id, amount, status, created_at, payme_id FROM transactions WHERE payme_id IS NOT NULL AND created_at IS NOT NULL",
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                t_id, user_id, amount, status, created_at, payme_id = row
                if not created_at:
                    continue
                try:
                    from datetime import datetime as _dt
                    dt = _dt.fromisoformat(created_at if '+' in created_at or 'Z' in created_at else created_at + '+00:00')
                    ts_ms = int(dt.timestamp() * 1000)
                except Exception:
                    continue
                if from_ms <= ts_ms <= to_ms:
                    result.append((t_id, user_id, amount, status, created_at, payme_id, ts_ms))
            return result

    async def update_balance(self, user_id, amount, add=True):
        async with await self._connect() as db:
            if add:
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            else:
                await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def get_balance(self, user_id):
        async with await self._connect() as db:
            cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_vip_tariffs(self):
        async with await self._connect() as db:
            cursor = await db.execute("SELECT id, price, days FROM tariffs")
            return await cursor.fetchall()
