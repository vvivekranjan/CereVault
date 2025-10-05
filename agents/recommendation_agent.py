import sqlite3
from datetime import datetime
import pandas as pd

class RecommendationAgent:
    def __init__(self):
        self.portfolio_conn = sqlite3.connect('portfolio.db', check_same_thread=False)
        self.market_conn = sqlite3.connect('market_data.db', check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.market_conn:
            self.market_conn.execute('''CREATE TABLE IF NOT EXISTS recommendations
                             (id INTEGER PRIMARY KEY, 
                              user_id TEXT, 
                              recommendation TEXT, 
                              confidence REAL, 
                              timestamp DATETIME)''')

    def _get_portfolio_risk(self, user_id):
        risk_conn = sqlite3.connect('portfolio.db')
        risk_metrics = pd.read_sql(f"SELECT * FROM risk_metrics WHERE user_id = '{user_id}' ORDER BY timestamp DESC LIMIT 1", risk_conn)
        return risk_metrics.iloc[0] if not risk_metrics.empty else None

    def _get_sentiment_data(self):
        return pd.read_sql("SELECT * FROM sentiment_reports ORDER BY timestamp DESC LIMIT 5", self.market_conn)

    def generate_recommendations(self, user_id):
        portfolio = pd.read_sql(f"SELECT * FROM portfolio WHERE user_id = '{user_id}'", self.portfolio_conn)
        risk_metrics = self._get_portfolio_risk(user_id)
        sentiment_data = self._get_sentiment_data()
        
        recommendations = []
        
        # Risk-based recommendations
        if risk_metrics and risk_metrics['var_percentage'] > 5:
            recommendations.append({
                'type': 'risk',
                'message': f'High portfolio risk ({risk_metrics["var_percentage"]:.1f}% VaR). Consider diversifying high-risk positions.',
                'confidence': 0.8
            })
        
        # Sentiment-based recommendations
        negative_assets = []
        positive_opportunities = []
        
        for _, row in sentiment_data.iterrows():
            if row['sentiment_label'] == 'negative':
                # Check if user holds this asset
                matching = portfolio[portfolio['symbol'] == row['title'].split()[0]]
                if not matching.empty:
                    negative_assets.append({
                        'symbol': row['title'].split()[0],
                        'reason': row['summary'],
                        'confidence': 0.7
                    })
            elif row['sentiment_label'] == 'positive' and len(positive_opportunities) < 2:
                positive_opportunities.append({
                    'symbol': row['title'].split()[0],
                    'reason': row['summary'],
                    'confidence': 0.65
                })
        
        # Add negative asset recommendations
        for asset in negative_assets:
            recommendations.append({
                'type': 'sentiment',
                'message': f'Consider reviewing position in {asset["symbol"]} due to negative sentiment: {asset["reason"]}',
                'confidence': asset["confidence"]
            })
        
        # Add positive opportunity recommendations
        for opp in positive_opportunities:
            recommendations.append({
                'type': 'opportunity',
                'message': f'Positive sentiment detected for {opp["symbol"]}: {opp["reason"]} - may warrant consideration',
                'confidence': opp["confidence"]
            })
        
        # Store recommendations
        with self.market_conn:
            for rec in recommendations:
                self.market_conn.execute(
                    'INSERT INTO recommendations (user_id, recommendation, confidence, timestamp) VALUES (?, ?, ?, ?)',
                    (user_id, rec['message'], rec['confidence'], datetime.now())
                )
        
        return recommendations

    def get_user_recommendations(self, user_id, limit=5):
        return self.market_conn.execute(
            'SELECT * FROM recommendations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', 
            (user_id, limit)
        ).fetchall()
