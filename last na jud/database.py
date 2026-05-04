import sqlite3
import hashlib
from datetime import datetime

class Database:
    def __init__(self, db_name="expensetrack.db"):
        self.db_name = db_name
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Login history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Expenses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date DATE NOT NULL,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Income
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source TEXT NOT NULL,
                amount REAL NOT NULL,
                date DATE NOT NULL,
                time TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Savings goals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                goal_name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                saved_amount REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
        conn.close()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username, email, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            hashed = self.hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed)
            )
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def authenticate_user(self, username_or_email, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        hashed = self.hash_password(password)
        cursor.execute(
            "SELECT id, username, email FROM users WHERE (username = ? OR email = ?) AND password = ?",
            (username_or_email, username_or_email, hashed)
        )
        user = cursor.fetchone()
        if user:
            cursor.execute(
                "INSERT INTO login_history (user_id) VALUES (?)",
                (user[0],)
            )
            conn.commit()
        conn.close()
        return user

    def add_expense(self, user_id, title, amount, category, date, notes=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, amount, category, date, notes)
        )
        conn.commit()
        conn.close()

    def get_expenses(self, user_id, filter_by=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT id, title, amount, category, date, notes FROM expenses WHERE user_id = ?"
        params = [user_id]
        if filter_by == "week":
            query += " AND date >= date('now', '-7 days')"
        elif filter_by == "month":
            query += " AND date >= date('now', 'start of month')"
        query += " ORDER BY date DESC"
        cursor.execute(query, params)
        expenses = cursor.fetchall()
        conn.close()
        return expenses

    def get_total_expenses(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?", (user_id,))
        total, count = cursor.fetchone()
        conn.close()
        return total or 0, count or 0

    def get_expenses_by_category(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category",
            (user_id,)
        )
        result = cursor.fetchall()
        conn.close()
        return result

    def add_income(self, user_id, source, amount, date, time, notes=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO income (user_id, source, amount, date, time, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, source, amount, date, time, notes)
        )
        conn.commit()
        conn.close()

    def get_income(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, source, amount, date, time, notes FROM income WHERE user_id = ? ORDER BY date DESC",
            (user_id,)
        )
        income = cursor.fetchall()
        conn.close()
        return income

    def get_total_income(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM income WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0] or 0
        conn.close()
        return total

    def add_savings_goal(self, user_id, goal_name, target_amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO savings_goals (user_id, goal_name, target_amount) VALUES (?, ?, ?)",
            (user_id, goal_name, target_amount)
        )
        conn.commit()
        conn.close()

    def get_savings_goals(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, goal_name, target_amount, saved_amount FROM savings_goals WHERE user_id = ?",
            (user_id,)
        )
        goals = cursor.fetchall()
        conn.close()
        return goals

    def update_savings(self, user_id, goal_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE savings_goals SET saved_amount = saved_amount + ? WHERE id = ? AND user_id = ?",
            (amount, goal_id, user_id)
        )
        conn.commit()
        conn.close()

    def get_user_info(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_login_history(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT login_time FROM login_history WHERE user_id = ? ORDER BY login_time DESC LIMIT 5",
            (user_id,)
        )
        history = cursor.fetchall()
        conn.close()
        return history

    def delete_all_user_data(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM income WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM savings_goals WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM login_history WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()