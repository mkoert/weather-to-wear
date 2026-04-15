"""
PostgreSQL Database Connection Module
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

logger = logging.getLogger('weather-app.db')


class DatabaseConnection:
    """PostgreSQL database connection handler"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DATABASE_URL', 'localhost'),
            'user': os.getenv('DATABASE_USER', 'postgres'),
            'password': os.getenv('DATABASE_PASSWORD', ''),
            'database': os.getenv('DATABASE_NAME', 'weather_to_wear'),
            'port': int(os.getenv('DATABASE_PORT', '5432')),
            'connect_timeout': 5,
            'options': '-c statement_timeout=5000'
        }
        logger.info("Connecting to PostgreSQL at %s:%s db=%s user=%s",
                     self.db_config['host'], self.db_config['port'],
                     self.db_config['database'], self.db_config['user'])

    @contextmanager
    def get_connection(self):
        """Get a database connection (context manager)"""
        conn = psycopg2.connect(**self.db_config)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_tables(self):
        """Initialize database tables"""
        logger.info("Creating tables if they don't exist")
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Weather cache table
            logger.info("Creating hourly_cache table")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hourly_cache (
                    id SERIAL PRIMARY KEY,
                    location VARCHAR(255) UNIQUE NOT NULL,
                    data JSONB NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    phone_number VARCHAR(20) UNIQUE NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    session_token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_hourly_cache_location
                ON hourly_cache(location)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_sessions_token
                ON user_sessions(session_token)
            ''')

    def execute_query(self, query, params=None, fetch=False):
        """Execute a query and optionally fetch results"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())

            if fetch:
                return cursor.fetchall()

            return cursor.rowcount


# Global database instance
db = DatabaseConnection()


def get_cached_data(location):
    """Retrieve cached weather data"""
    from datetime import datetime, timedelta

    query = '''
        SELECT data, timestamp
        FROM hourly_cache
        WHERE location = %s
    '''

    result = db.execute_query(query, (location,), fetch=True)

    if result:
        data, timestamp = result[0]['data'], result[0]['timestamp']

        # Check if cache is less than 1 hour old
        if datetime.now() - timestamp < timedelta(hours=1):
            return data

    return None


def cache_data(location, data):
    """Store weather data in cache"""
    from datetime import datetime
    from psycopg2.extras import Json

    query = '''
        INSERT INTO hourly_cache (location, data, timestamp)
        VALUES (%s, %s, %s)
        ON CONFLICT (location)
        DO UPDATE SET data = EXCLUDED.data, timestamp = EXCLUDED.timestamp
    '''

    # Use psycopg2's Json adapter for JSONB column
    params = (location, Json(data), datetime.now())
    db.execute_query(query, params)
