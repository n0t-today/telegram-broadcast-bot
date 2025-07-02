import aiosqlite
import asyncio
from typing import List, Dict, Optional
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    shop_address TEXT NOT NULL,
                    is_banned INTEGER DEFAULT 0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def add_user(self, user_id: int, username: str, full_name: str, city: str, shop_address: str):
        """Добавление пользователя в базу данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, username, full_name, city, shop_address)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, full_name, city, shop_address))
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение данных пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, username, full_name, city, shop_address, is_banned
                FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "username": row[1],
                        "full_name": row[2],
                        "city": row[3],
                        "shop_address": row[4],
                        "is_banned": bool(row[5])
                    }
                return None
    
    async def get_all_users(self) -> List[Dict]:
        """Получение всех незаблокированных пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT user_id, username, full_name, city, shop_address
                FROM users WHERE is_banned = 0
            """) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "user_id": row[0],
                        "username": row[1],
                        "full_name": row[2],
                        "city": row[3],
                        "shop_address": row[4]
                    }
                    for row in rows
                ]
    
    async def ban_user_by_username(self, username: str) -> bool:
        """Блокировка пользователя по username"""
        username = username.replace("@", "")  # Убираем @ если есть
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE users SET is_banned = 1 
                WHERE username = ? AND is_banned = 0
            """, (username,))
            await db.commit()
            return cursor.rowcount > 0
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Проверка, заблокирован ли пользователь"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT is_banned FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False

# Создаем экземпляр базы данных
db = Database() 