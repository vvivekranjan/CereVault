# Financial AI Dashboard (Cerebras-Powered)

**AI-Powered Financial Planning & Stock Analysis Platform**

---

## 🚀 Features

- Real-time portfolio tracking with visualization
- Risk analysis using Cerebras Monte Carlo simulations
- Market news summarization via Cerebras LLM
- Personalized financial recommendations
- Voice/chat interface with LiveKit integration

---

## 🧠 Architecture

**Frontend**: React + Chart.js  
**Backend**: Flask (app.py)  
**AI Backend**: Cerebras Cluster
**Voice**: LiveKit 
**Data Storage**: Postgres/TimescaleDB + Vector DB

---

## 🛠 Tech Stack

- **Frontend**: React, Axios, Chart.js
- **Backend**: Flask, Cerebras SDK
- **AI**: Cerebras LLM, Prophet/ARIMA models
- **Voice**: LiveKit
- **Database**: Postgres/TimescaleDB, Redis, Weaviate

---

## 📦 Setup

1. Clone repository
2. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
3. Start backend (Flask + Cerebras integration)
4. Start frontend:
   ```bash
   npm start
   ```

---

## 🔑 API Keys

- **Cerebras**: `csk-9ff2v5t9cvjdrfdcckv238rw6cxccvjjh3rdnm9cxekx5vff`
- **LiveKit**: `APIX8QG6eTDitCT`

*(Store in .env file for security)*

---

## 📊 How It Works

1. User interacts via chat/voice
2. Cerebras handles LLM inference + time-series forecasting
3. Frontend displays dynamic visualizations
4. Risk analysis uses Monte Carlo simulations
5. Market insights auto-summarized from news
