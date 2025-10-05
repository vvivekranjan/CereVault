import sqlite3
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np

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
