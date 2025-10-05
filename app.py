from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from datetime import datetime
import os
import sqlite3
import pandas as pd
from flask import Flask, jsonify, request

# Load environment variables
load_dotenv()

app = Flask(__name__)
cerebras_client = Cerebras(api_key=os.getenv('CEREBRAS_API_KEY'))

# Initialize agents
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

def generate_synthetic_data(days=30):
    """Generate synthetic financial time series data"""
    return {
        'dates': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') 
                for i in range(days)][::-1],
        'values': [round(100000 * (1 + random.uniform(-0.02, 0.03)), 2) 
                 for _ in range(days)]
    }

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

class RiskAnalyzer:
    def __init__(self):
        self.market_conn = sqlite3.connect('market_data.db', check_same_thread=False)
        self.portfolio_conn = sqlite3.connect('portfolio.db', check_same_thread=False)

    def _get_historical_prices(self, symbol, days=30):
        query = '''SELECT timestamp, price 
                   FROM market_data 
                   WHERE symbol = ? 
                   ORDER BY timestamp DESC 
                   LIMIT ?'''
        df = pd.read_sql(query, self.market_conn, params=(symbol, days))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        return df

    def calculate_value_at_risk(self, user_id, confidence_level=0.95, days=30):
        portfolio = pd.read_sql(f"SELECT * FROM portfolio WHERE user_id = '{user_id}'", self.portfolio_conn)
        total_value = 0
        var_total = 0
        
        for _, row in portfolio.iterrows():
            symbol = row['symbol']
            quantity = row['quantity']
            price_data = self._get_historical_prices(symbol, days)
            
            if len(price_data) < 2:
                continue
                
            returns = price_data['price'].pct_change().dropna()
            if len(returns) == 0:
                continue
                
            var = np.percentile(returns, 100 * (1 - confidence_level))
            position_value = quantity * price_data['price'].iloc[-1]
            var_total += position_value * var
            total_value += position_value
            
        return abs(var_total), total_value

    def perform_stress_test(self, user_id, crash_scenarios=[-0.2, -0.5, -0.7]):
        portfolio = pd.read_sql(f"SELECT * FROM portfolio WHERE user_id = '{user_id}'", self.portfolio_conn)
        results = {}
        
        for scenario in crash_scenarios:
            scenario_loss = 0
            for _, row in portfolio.iterrows():
                symbol = row['symbol']
                quantity = row['quantity']
                price_data = self._get_historical_prices(symbol)
                
                if not price_data.empty:
                    current_price = price_data['price'].iloc[-1]
                    crash_price = current_price * (1 + scenario)
                    loss = quantity * (current_price - crash_price)
                    scenario_loss += loss
                    
            results[scenario] = scenario_loss
            
        return results

    def get_risk_metrics(self, user_id):
        var, total_value = self.calculate_value_at_risk(user_id)
        portfolio = pd.read_sql(f"SELECT * FROM portfolio WHERE user_id = '{user_id}'", self.portfolio_conn)
        
        return {
            'timestamp': datetime.now(),
            'total_portfolio_value': total_value,
            'value_at_risk_95': var,
            'var_percentage': (var/total_value)*100 if total_value > 0 else 0,
            'position_count': len(portfolio)
        }

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
            summary = self._generate_summary(article[2])
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
        
        if risk_metrics and risk_metrics['var_percentage'] > 5:
            recommendations.append({
                'type': 'risk',
                'message': f'High portfolio risk ({risk_metrics["var_percentage"]:.1f}% VaR). Consider diversifying high-risk positions.',
                'confidence': 0.8
            })
        
        negative_assets = []
        positive_opportunities = []
        
        for _, row in sentiment_data.iterrows():
            if row['sentiment_label'] == 'negative':
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
        
        for asset in negative_assets:
            recommendations.append({
                'type': 'sentiment',
                'message': f'Consider reviewing position in {asset["symbol"]} due to negative sentiment: {asset["reason"]}',
                'confidence': asset["confidence"]
            })
        
        for opp in positive_opportunities:
            recommendations.append({
                'type': 'opportunity',
                'message': f'Positive sentiment detected for {opp["symbol"]}: {opp["reason"]} - may warrant consideration',
                'confidence': opp["confidence"]
            })
        
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
        history = self.get_conversation_history(user_id)
        context = "Previous conversation:\n" + "\n".join([f"Q: {row[2]} A: {row[3]}" for row in history]) if history else ""
        
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

# Initialize all agents
data_agent = DataIngestionAgent()
portfolio_agent = PortfolioTracker()
risk_agent = RiskAnalyzer()
market_insight_agent = MarketInsightAgent()
recommendation_agent = RecommendationAgent()
conversational_agent = ConversationalAgent()

@app.route('/api/risk-analysis', methods=['GET'])
def get_risk_analysis():
    user_id = request.args.get('user_id', 'default_user')
    risk_metrics = risk_agent.get_risk_metrics(user_id)
    return jsonify(risk_metrics)

@app.route('/api/market-insights', methods=['GET'])
def get_market_insights():
    reports = market_insight_agent.get_latest_reports()
    return jsonify([dict(row) for row in reports])

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    user_id = request.args.get('user_id', 'default_user')
    recs = recommendation_agent.get_user_recommendations(user_id)
    return jsonify([dict(row) for row in recs])

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data.get('user_id', 'default_user')
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    response, confidence = conversational_agent.generate_response(
        user_id, 
        question, 
        {
            'portfolio': portfolio_agent,
            'risk': risk_agent,
            'market_insight': market_insight_agent,
            'recommendation': recommendation_agent
        }
    )
    
    conversational_agent.add_conversation(user_id, question, response)
    
    return jsonify({
        'response': response,
        'confidence': confidence
    })

@app.route('/api/risk-analysis', methods=['GET'])
def get_risk_analysis():
    # Example Cerebras Monte Carlo simulation integration
    try:
        # This would be replaced with actual Cerebras API call
        # For demonstration, we'll simulate a response
        volatility = random.uniform(0.1, 0.3)
        downside_risk = random.uniform(0.05, 0.2)
        
        return jsonify({
            'score': max(0, min(100, int(70 + (volatility * 30)))),
            'volatility': round(volatility, 2),
            'downsideRisk': round(downside_risk, 2),
            'timeHorizon': '30D'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-insights', methods=['GET'])
def get_market_insights():
    # Example Cerebras LLM integration for market analysis
    try:
        # This would be replaced with actual LLM call
        # For demonstration, we'll simulate a response
        sectors = ['Tech', 'Healthcare', 'Energy', 'Finance']
        random_sector = random.choice(sectors)
        sentiment = random.choice(['positive', 'neutral', 'negative'])
        
        return jsonify({
            'summary': f'{random_sector} sector shows {sentiment} momentum with recent regulatory changes',
            'sentiment': sentiment,
            'impact': random.uniform(0.5, 2.5),
            'trendingAssets': [f'{random_sector} ETF', f'{random_sector} Index']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    # Example Cerebras LLM integration for personalized advice
    try:
        # This would be replaced with actual LLM call
        # For demonstration, we'll simulate a response
        return jsonify({
            'actions': [
                'Consider increasing exposure to Energy sector based on current trends',
                'Rebalance portfolio to maintain target asset allocation',
                'Review options strategies for downside protection'
            ],
            'confidence': random.uniform(0.6, 0.9),
            'timeframe': '3-6 months'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
