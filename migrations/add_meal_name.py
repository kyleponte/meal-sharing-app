import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def upgrade():
    with app.app_context():
        # Add name column to meal table
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE meal ADD COLUMN name VARCHAR(100) NOT NULL DEFAULT \'Untitled Meal\''))
            conn.commit()

def downgrade():
    with app.app_context():
        # Remove name column from meal table
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE meal DROP COLUMN name'))
            conn.commit()

if __name__ == '__main__':
    upgrade() 