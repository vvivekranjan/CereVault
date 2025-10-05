import requests
import sqlite3
from datetime import datetime
import os

class DataIngestionAgent:
    def __init__(self):
        self.api_keys = {
            'market': os.getenv('MARKET_API_KEY'),
            'news': os.getenv('NEWS_API_KEY')
        }
        self.conn = sqlite3.connect('market_data.db', check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS market_data
                             (id INTEGER PRIMARY KEY, 
                              symbol TEXT, 
                              price REAL, 
                              timestamp DATETIME)''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS news_articles
                             (id INTEGER PRIMARY KEY, 
                              title TEXT, 
                              content TEXT, 
                              source TEXT, 
                              timestamp DATETIME)''')

    def fetch_market_data(self, symbols):
        for symbol in symbols:
            response = requests.get(
                f'https://api.marketdata.com/v1/quotes/{symbol}',
                headers={'Authorization': f'Bearer {self.api_keys["market"]}'} 
            )
            if response.status_code == 200:
                data = response.json()
                self.conn.execute(
                    'INSERT INTO market_data (symbol, price, timestamp) VALUES (?, ?, ?)',
                    (symbol, data['price'], datetime.now())
                )
        self.conn.commit()

    def fetch_news(self, topics):
        response = requests.get(
            'https://api.newsdata.com/v1/news',
            params={'api-key': self.api_keys['news'], 'q': ','.join(topics)}
        )
        if response.status_code == 200:
            for article in response.json()['results']:
                self.conn.execute(
                    'INSERT INTO news_articles (title, content, source, timestamp) VALUES (?, ?, ?, ?)',
                    (article['title'], article['content'], article['source'], datetime.now())
                )
            self.conn.commit()

    def get_latest_data(self, table, limit=10):
        return self.conn.execute(f'SELECT * FROM {table} ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
