import sqlite3
from datetime import datetime
from textblob import TextBlob

class MarketInsightAgent:
    def __init__(self):
        self.conn = sqlite3.connect('market_data.db', check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS sentiment_reports
                             (id INTEGER PRIMARY KEY, 
                              article_id INTEGER, 
                              summary TEXT, 
                              sentiment_polarity REAL, 
                              sentiment_label TEXT, 
                              timestamp DATETIME,
                             FOREIGN KEY(article_id) REFERENCES news_articles(id))''')

    def _get_recent_articles(self, limit=5):
        return self.conn.execute(
            'SELECT * FROM news_articles ORDER BY timestamp DESC LIMIT ?', 
            (limit,)
        ).fetchall()

    def _generate_summary(self, content, max_length=150):
        # Simple summary by truncating content (replace with NLP model if needed)
        if len(content) <= max_length:
            return content
        return content[:max_length].rsplit(' ', 1)[0] + '...'

    def analyze_sentiment(self, text):
        analysis = TextBlob(text)
        polarity = analysis.sentiment.polarity
        if polarity > 0.1:
            return 'positive', polarity
        elif polarity < -0.1:
            return 'negative', polarity
        else:
            return 'neutral', polarity

    def generate_insight_report(self):
        articles = self._get_recent_articles()
        reports = []
        
        for article in articles:
            summary = self._generate_summary(article[2])  # content field
            sentiment_label, polarity = self.analyze_sentiment(summary)
            
            self.conn.execute(
                'INSERT INTO sentiment_reports (article_id, summary, sentiment_polarity, sentiment_label, timestamp) VALUES (?, ?, ?, ?, ?)',
                (article[0], summary, polarity, sentiment_label, datetime.now())
            )
            reports.append({
                'title': article[1],
                'summary': summary,
                'sentiment': sentiment_label,
                'polarity': round(polarity, 3)
            })
        
        self.conn.commit()
        return reports

    def get_latest_reports(self, limit=5):
        return self.conn.execute(
            'SELECT * FROM sentiment_reports ORDER BY timestamp DESC LIMIT ?', 
            (limit,)
        ).fetchall()
