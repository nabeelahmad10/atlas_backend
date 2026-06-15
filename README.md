# Atlas Marketing OS - Backend API
> Backend services for the AI-Native Decision Intelligence Engine.

**Built for the Xeno Engineering Evaluation.**

## Product Vision
Legacy CRMs act as static filing cabinets requiring operators to write complex SQL queries just to find an audience. **Atlas Marketing OS** flips the paradigm: it acts as a **Decision Intelligence Engine**. You provide the business intent (e.g., *"Recover dormant VIP revenue"*), and the system autonomously translates that intent into data queries, formulates a mathematically backed strategy, executes the campaign via decoupled microservices, and conducts its own post-mortem analysis.

## Features
- **Agentic Workflow:** Translates natural language goals into precise database queries using a JSON AST layer, preventing LLM hallucination.
- **Deterministic Predictions:** Projects Open Rates, CTRs, and Revenue based on real audience counts and hardcoded baseline math, not LLM guesses.
- **Webhook-Driven Event Sourcing:** A decoupled Channel Service simulates asynchronous delivery (Email/SMS/WhatsApp) and fires webhooks back to the main API, appending to an immutable event ledger.
- **Real-Time Execution Funnel:** The Next.js frontend polls the webhook ledger, rendering a live, smoothly animating execution funnel as messages are delivered and opened in real-time.
- **AI Post-Mortem Analysis:** Automatically runs a post-campaign analysis based on the final webhook event counts to determine exactly why a campaign succeeded or failed.
- **Premium UI:** Designed with a Linear/Vercel-inspired glassmorphic aesthetic featuring 150-300ms micro-animations.

## Architecture
- **Backend Core:** FastAPI (Python), strictly typed with Pydantic.
- **Database:** SQLite (Relational, strictly normalized, event-driven).
- **AI Engine:** Mistral AI.
- **Microservices:** A completely independent `channel-service` running on its own port simulating 3rd party providers (like Twilio/SendGrid).

## Local Setup

### 1. Backend API
```bash
cd backend
python -m venv venv
source venv/Scripts/activate # Windows
pip install -r requirements.txt
cp .env.example .env
# Start the backend on port 8000
uvicorn main:app --reload --port 8000
```

### 2. Channel Service (Simulated External Provider)
Open a new terminal:
```bash
cd channel-service
python -m venv venv
source venv/Scripts/activate # Windows
pip install -r requirements.txt
cp .env.example .env
# Start the channel service on port 8001
uvicorn main:app --reload --port 8001
```


## System Design Decisions & Tradeoffs
1. **SQLite over PostgreSQL:** Used for the MVP to allow zero-config evaluations. However, the schema is strictly normalized and fully compatible with Postgres. Transitioning requires only updating the SQLAlchemy connection string.
2. **JSON AST over Text-to-SQL:** The LLM generates a JSON filter instead of raw SQL. This acts as a security abstraction layer, preventing SQL injection and ensuring the LLM can only query explicitly whitelisted schema fields.
3. **Decoupled Microservice:** Built the channel dispatcher as a separate FastAPI app to prove competency in distributed systems and asynchronous webhook processing, a critical requirement for massive scale.

## Future Improvements
- **Message Queues:** Replace synchronous webhook HTTP calls with Kafka or Redis Pub/Sub for scale.
- **Streaming UI:** Transition the real-time polling Event Funnel to WebSockets or Server-Sent Events (SSE).
