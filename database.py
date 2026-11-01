import sqlite3
from pathlib import Path

from flask import g


BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "codex.db"


def get_db():
    """Devuelve la conexión SQLite asociada a la petición actual."""
    if "db" not in g:
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    """Cierra la conexión de la petición, si existe."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Crea únicamente las tablas e índices que aún no existan."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                system TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'Otro',
                summary TEXT DEFAULT '',
                description TEXT DEFAULT '',
                secret_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                location_id INTEGER,
                name TEXT NOT NULL,
                character_type TEXT NOT NULL DEFAULT 'narrative',
                ancestry TEXT DEFAULT '',
                age TEXT DEFAULT '',
                occupation TEXT DEFAULT '',
                character_class TEXT DEFAULT '',
                level INTEGER,
                summary TEXT DEFAULT '',
                personality TEXT DEFAULT '',
                biography TEXT DEFAULT '',
                motivations TEXT DEFAULT '',
                armor_class INTEGER,
                hit_points INTEGER,
                perception TEXT DEFAULT '',
                saving_throws TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                attacks TEXT DEFAULT '',
                abilities TEXT DEFAULT '',
                portrait_url TEXT DEFAULT '',
                secret_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations(id)
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS character_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                related_character_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (related_character_id) REFERENCES characters(id)
                    ON DELETE CASCADE,
                UNIQUE (character_id, related_character_id, relationship_type),
                CHECK (character_id != related_character_id)
            );

            CREATE TABLE IF NOT EXISTS factions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                faction_type TEXT NOT NULL DEFAULT 'Otra',
                summary TEXT DEFAULT '',
                description TEXT DEFAULT '',
                ideology TEXT DEFAULT '',
                goals TEXT DEFAULT '',
                hierarchy TEXT DEFAULT '',
                secret_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS faction_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faction_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'Miembro',
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (faction_id) REFERENCES factions(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id)
                    ON DELETE CASCADE,
                UNIQUE (faction_id, character_id)
            );

            CREATE TABLE IF NOT EXISTS faction_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faction_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL DEFAULT 'Sede',
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (faction_id) REFERENCES factions(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations(id)
                    ON DELETE CASCADE,
                UNIQUE (faction_id, location_id)
            );

            CREATE TABLE IF NOT EXISTS faction_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faction_id INTEGER NOT NULL,
                related_faction_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (faction_id) REFERENCES factions(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (related_faction_id) REFERENCES factions(id)
                    ON DELETE CASCADE,
                UNIQUE (faction_id, related_faction_id, relationship_type),
                CHECK (faction_id != related_faction_id)
            );

            CREATE TABLE IF NOT EXISTS creatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                location_id INTEGER,
                name TEXT NOT NULL,
                creature_type TEXT NOT NULL DEFAULT 'Criatura',
                level INTEGER,
                rarity TEXT NOT NULL DEFAULT 'Común',
                alignment TEXT DEFAULT '',
                size TEXT DEFAULT '',
                ancestry TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                description TEXT DEFAULT '',
                armor_class INTEGER,
                hit_points INTEGER,
                perception TEXT DEFAULT '',
                saving_throws TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                speeds TEXT DEFAULT '',
                attacks TEXT DEFAULT '',
                abilities TEXT DEFAULT '',
                weaknesses TEXT DEFAULT '',
                resistances TEXT DEFAULT '',
                immunities TEXT DEFAULT '',
                loot TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                secret_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations(id)
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                location_id INTEGER,
                name TEXT NOT NULL,
                item_type TEXT NOT NULL DEFAULT 'Otro',
                rarity TEXT NOT NULL DEFAULT 'Común',
                level INTEGER,
                price TEXT DEFAULT '',
                bulk TEXT DEFAULT '',
                traits TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                description TEXT DEFAULT '',
                activation TEXT DEFAULT '',
                effects TEXT DEFAULT '',
                usage TEXT DEFAULT '',
                owner TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                secret_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations(id)
                    ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_locations_campaign
                ON locations(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_characters_campaign
                ON characters(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_characters_location
                ON characters(location_id);
            CREATE INDEX IF NOT EXISTS idx_relationship_source
                ON character_relationships(character_id);
            CREATE INDEX IF NOT EXISTS idx_relationship_target
                ON character_relationships(related_character_id);
            CREATE INDEX IF NOT EXISTS idx_factions_campaign
                ON factions(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_faction_memberships_faction
                ON faction_memberships(faction_id);
            CREATE INDEX IF NOT EXISTS idx_faction_memberships_character
                ON faction_memberships(character_id);
            CREATE INDEX IF NOT EXISTS idx_faction_locations_faction
                ON faction_locations(faction_id);
            CREATE INDEX IF NOT EXISTS idx_faction_locations_location
                ON faction_locations(location_id);
            CREATE INDEX IF NOT EXISTS idx_faction_relationships_source
                ON faction_relationships(faction_id);
            CREATE INDEX IF NOT EXISTS idx_faction_relationships_target
                ON faction_relationships(related_faction_id);
            CREATE INDEX IF NOT EXISTS idx_creatures_campaign
                ON creatures(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_creatures_location
                ON creatures(location_id);
            CREATE INDEX IF NOT EXISTS idx_items_campaign
                ON items(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_items_location
                ON items(location_id);
        """)

        db.execute("""
            INSERT INTO campaigns (name, system, description)
            SELECT ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM campaigns WHERE name = ?
            )
        """, (
            "Valdren Hollow",
            "Pathfinder 2e Remaster",
            "Campaña principal de Valdren Hollow.",
            "Valdren Hollow",
        ))

    app.teardown_appcontext(close_db)
