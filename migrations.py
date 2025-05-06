from app import app, db
from sqlalchemy import text

def add_description_column():
    with app.app_context():
        # Add description column to meal table
        db.session.execute(text('ALTER TABLE meal ADD COLUMN IF NOT EXISTS description TEXT'))
        db.session.commit()
        print("Description column added successfully!")

def add_bio_column():
    with app.app_context():
        # Add bio column to user table
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS bio TEXT'))
        db.session.commit()
        print("Bio column added successfully!")

def create_rating_table():
    with app.app_context():
        # Create rating table
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS rating (
                id SERIAL PRIMARY KEY,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                rater_id INTEGER NOT NULL REFERENCES "user"(id),
                rated_user_id INTEGER NOT NULL REFERENCES "user"(id),
                meal_id INTEGER NOT NULL REFERENCES meal(id),
                rating_type VARCHAR(10) NOT NULL,
                CONSTRAINT valid_rating CHECK (rating >= 1 AND rating <= 5)
            )
        '''))
        db.session.commit()
        print("Rating table created successfully!")

if __name__ == '__main__':
    add_description_column()
    add_bio_column()
    create_rating_table()
    print("All migrations completed successfully!") 