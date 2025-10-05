import sqlite3
from datetime import datetime

class ConversationalAgent:
    def __init__(self):
        self.conn = sqlite3.connect('conversation.db', check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS conversation_history
                             (id INTEGER PRIMARY KEY, 
                              user_id TEXT, 
                              question TEXT, 
                              answer TEXT, 
                              timestamp DATETIME)''')

    def add_conversation(self, user_id, question, answer):
        with self.conn:
            self.conn.execute(
                'INSERT INTO conversation_history (user_id, question, answer, timestamp) VALUES (?, ?, ?, ?)',
                (user_id, question, answer, datetime.now())
            )

    def get_conversation_history(self, user_id, limit=5):
        return self.conn.execute(
            'SELECT * FROM conversation_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', 
            (user_id, limit)
        ).fetchall()

    def generate_response(self, user_id, question, other_agents):
        # Simple Q&A with memory integration
        history = self.get_conversation_history(user_id)
        context = "Previous conversation:\n" + "\n".join([f"Q: {row[2]} A: {row[3]}" for row in history]) if history else ""
        
        # Basic routing to other agents
        if "portfolio" in question.lower():
            portfolio_data = other_agents['portfolio'].get_user_portfolio(user_id)
            return f"Your portfolio: {portfolio_data}", 0.9
        elif "risk" in question.lower():
            risk_data = other_agents['risk'].get_risk_metrics(user_id)
            return f"Risk metrics: {risk_data}", 0.85
        elif "recommendations" in question.lower():
            recs = other_agents['recommendation'].get_user_recommendations(user_id)
            return f"Recommendations: {recs}", 0.8
        elif "news" in question.lower():
            news = other_agents['market_insight'].get_latest_reports()
            return f"Latest news: {news}", 0.75
        else:
            return "I can help with portfolio analysis, risk metrics, recommendations, and market news. What would you like to know?", 0.6
