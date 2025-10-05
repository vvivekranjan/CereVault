import requests
import sqlite3
from datetime import datetime
import os

class PortfolioTracker:
    def __init__(self):
        self.api_key = os.getenv('BROKERAGE_API_KEY')
        self.conn = sqlite3.connect('portfolio.db', check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS portfolio
                             (id INTEGER PRIMARY KEY, 
                              user_id TEXT, 
                              symbol TEXT, 
                              quantity REAL, 
                              purchase_price REAL, 
                              timestamp DATETIME)''')

    def fetch_portfolio_data(self, user_id):
        response = requests.get(
            'https://api.brokerage.com/v1/portfolio',
            headers={'Authorization': f'Bearer {self.api_key}'},
            params={'user_id': user_id}
        )
        if response.status_code == 200:
            positions = response.json()['positions']
            with self.conn:
                for position in positions:
                    self.conn.execute(
                        'INSERT INTO portfolio (user_id, symbol, quantity, purchase_price, timestamp) VALUES (?, ?, ?, ?, ?)',
                        (user_id, position['symbol'], position['quantity'], position['price'], datetime.now())
                    )
            return positions
        return None

    def get_user_portfolio(self, user_id, limit=10):
        return self.conn.execute(
            'SELECT * FROM portfolio WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
