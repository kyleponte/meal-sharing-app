# Meal Sharing App

A Flask web application for sharing and discovering meals in your community.

## Setup Instructions

1. Clone the repository:
```bash
git clone [your-repository-url]
cd meal-sharing-app
```

2. Create a virtual environment and activate it:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following content:
```
DATABASE_URL=your_database_url
SECRET_KEY=your-secret-key-here
```

## Database Setup Options

### Option 1: Shared Cloud Database (Recommended for collaboration)
Use a shared PostgreSQL database hosted on a cloud platform. This way, all collaborators will be working with the same data.

1. Get the shared database URL from your team lead
2. Put the URL in your `.env` file:
```
DATABASE_URL=postgresql://username:password@host:port/database
```

## Running the Application

```bash
python app.py
```

The application should now be running at `http://localhost:5000`

## Features
- User authentication (signup/login)
- Post meals with multiple dishes
- Browse available meals
- Delete your own meals

## Database Schema
- Users: Stores user accounts and authentication
- Meals: Stores meal events with location, time, and guest limits
- Dishes: Stores dishes associated with each meal