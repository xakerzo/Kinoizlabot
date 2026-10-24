"""
Railway PostgreSQL → Yangi PostgreSQL (Coolify) ko'chirish skripti
Ishlatish:
    1. RAILWAY_DATABASE_URL ni to'ldiring
    2. NEW_DATABASE_URL ni to'ldiring (Coolify PostgreSQL)
    3. python migrate_railway_to_local.py
"""

import psycopg2
from urllib.parse import urlparse

# ============================================================
# BU YERGA O'ZGARTIRING
# ============================================================
RAILWAY_DATABASE_URL = "postgresql://postgres:PASSWORD@junction.proxy.rlwy.net:PORT/railway"
NEW_DATABASE_URL = "postgresql://postgres:PASSWORD@localhost:5432/kino_bot"
# ============================================================

TABLES = [
    "bot_settings",
    "films",
    "premium_videos",
    "users",
    "channels",
    "insta_links",
    "partners",
    "premium_users",
    "bypass_requests",
    "ad_texts",
    "video_captions",
    "start_messages",
    "premium_texts",
    "video_stats",
    "total_stats",
    "caption_texts",
    "tariffs",
    "transactions",
]

def get_conn(url):
    r = urlparse(url)
    return psycopg2.connect(
        database=r.path[1:],
        user=r.username,
        password=r.password,
        host=r.hostname,
        port=r.port,
        sslmode='require' if 'railway' in url else 'prefer'
    )

def migrate():
    print("🔌 Railway ga ulanmoqda...")
    src = get_conn(RAILWAY_DATABASE_URL)
    src_cur = src.cursor()

    print("🔌 Yangi serverga ulanmoqda...")
    dst = get_conn(NEW_DATABASE_URL)
    dst_cur = dst.cursor()

    total_rows = 0

    for table in TABLES:
        try:
            # Railway dan o'qish
            src_cur.execute(f"SELECT * FROM {table}")
            rows = src_cur.fetchall()

            if not rows:
                print(f"  ⬜ {table}: bo'sh")
                continue

            # Ustun nomlarini olish
            col_names = [desc[0] for desc in src_cur.description]
            cols = ", ".join(col_names)
            placeholders = ", ".join(["%s"] * len(col_names))

            # Yangi serverga yozish
            for row in rows:
                try:
                    dst_cur.execute(
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                        row
                    )
                except Exception as e:
                    print(f"    ⚠️ Qator xatosi ({table}): {e}")

            dst.commit()
            total_rows += len(rows)
            print(f"  ✅ {table}: {len(rows)} ta qator ko'chirildi")

        except Exception as e:
            print(f"  ❌ {table}: {e}")
            dst.rollback()

    src.close()
    dst.close()
    print(f"\n🎉 Tayyor! Jami {total_rows} ta qator ko'chirildi!")

if __name__ == "__main__":
    migrate()
