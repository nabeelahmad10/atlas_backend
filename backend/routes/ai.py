"""
AI routes — Next-Generation AI Marketing Strategist.
"""

from fastapi import APIRouter, Depends
import aiosqlite
import json
import os
import httpx
from database import get_db
from models import (
    AISegmentRequest, 
    AISegmentResponse,
    AIStrategyRequest, 
    AIStrategyResponse,
    AICampaignAnalysisRequest,
    AICampaignAnalysisResponse,
    AIMessageRequest,
    AIMessageResponse
)
from query_builder import build_sql_from_filter

router = APIRouter(prefix="/api/ai", tags=["AI"])

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

DB_SCHEMA_RULES = """
Available Customer Fields for Filtering:
- city (e.g. Mumbai, Delhi, Bangalore, etc.)
- gender (Female, Male)
- tags (JSON array string containing: high-value, vip, frequent-buyer, new-customer, at-risk, dormant, deal-seeker, brand-loyal, seasonal-buyer)
- total_spent (numeric)
- total_orders (numeric)
- days_since_last_order (numeric)
- health_score (numeric 0-100)
- status (VIP Loyal Customer, Active Purchaser, At Risk, Likely To Churn)

Supported Operators:
- eq, neq, gt, lt, gte, lte, contains
"""


async def call_llm(messages: list, temperature: float = 0.3) -> str:
    """Call Mistral AI API."""
    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY not set.")

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MISTRAL_MODEL,
                "messages": messages,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


@router.post("/strategy", response_model=AIStrategyResponse)
async def ai_generate_strategy(request: AIStrategyRequest, db: aiosqlite.Connection = Depends(get_db)):
    """
    Generate a full marketing strategy based on a business goal.
    This runs a two-step AI pipeline:
    1. Translate goal -> JSON Filter
    2. Query DB for real stats -> Generate Strategy & Predictions
    """
    from fastapi import HTTPException
    
    # Guardrail against short gibberish prompts like "hi"
    if len(request.business_goal.strip()) < 10:
        raise HTTPException(
            status_code=400, 
            detail="Please provide a more descriptive business goal. (e.g. 'Reward our high-value customers')"
        )

    # Step 1: Generate Filter
    filter_prompt = [
        {
            "role": "system",
            "content": f"""You are a CRM Data Architect. Given a marketing goal, construct a JSON filter to identify the target audience.
{DB_SCHEMA_RULES}

CRITICAL INSTRUCTIONS:
1. Map user synonyms to the closest exact Available Customer Fields values. For example, if they ask for 'inactive' customers, map it to the 'dormant' tag or 'Likely To Churn' status.
2. DO NOT invent tags, statuses, or fields that are not explicitly listed in the schema.

Output MUST be valid JSON matching this schema:
{{
  "conditions": [
    {{"field": "...", "operator": "...", "value": "..."}}
  ],
  "logic": "AND"
}}"""
        },
        {
            "role": "user",
            "content": request.business_goal
        }
    ]

    try:
        filter_resp = await call_llm(filter_prompt)
        try:
            filter_json = json.loads(filter_resp)
        except json.JSONDecodeError:
            # Fallback to empty filter if LLM hallucinates non-JSON
            filter_json = {"conditions": [], "logic": "AND"}

        # Step 2: Execute Filter to get real stats
        sql_query, params = build_sql_from_filter(filter_json)
        
        # Get count
        count_cursor = await db.execute(f"SELECT COUNT(*) FROM ({sql_query})", params)
        real_reach = (await count_cursor.fetchone())[0]

        # Get avg stats for prediction context
        stats_cursor = await db.execute(f"""
            SELECT AVG(total_spent) as avg_spent, AVG(health_score) as avg_health 
            FROM ({sql_query})
        """, params)
        stats = await stats_cursor.fetchone()
        avg_spent = stats[0] or 0
        avg_health = stats[1] or 0

        # Step 3: Generate Deterministic Predictions
        base_ctr = 0.18
        audience_multiplier = 1.2 if avg_health > 60 else 0.8
        calculated_ctr = base_ctr * audience_multiplier
        # Assume 5% conversion rate on clicks
        calculated_revenue = round(calculated_ctr * real_reach * 0.05 * avg_spent, 2)

        # Step 4: Generate Strategy
        strategy_prompt = [
            {
                "role": "system",
                "content": f"""You are an AI Marketing Strategist. Generate a strategy based on the business goal and audience stats.
CRITICAL INSTRUCTION: You MUST use the following deterministic predictions derived from the historical database formulas. Do not hallucinate numbers.
- predicted_open_rate: 0.45
- predicted_ctr: {round(calculated_ctr, 3)}
- predicted_revenue: {calculated_revenue}

Output valid JSON matching this schema:
{{
  "business_objective": "...",
  "target_audience": "...",
  "recommended_channel": "...",
  "channel_reasoning": "... (Explain WHY the CTR is {round(calculated_ctr*100, 1)}% based on historical base rate and audience health multiplier)",
  "campaign_concept": "...",
  "predicted_open_rate": 0.45,
  "predicted_ctr": {round(calculated_ctr, 3)},
  "predicted_revenue": {calculated_revenue},
  "confidence_score": 0
}}"""
            },
            {
                "role": "user",
                "content": f"""
Business Goal: {request.business_goal}
Audience Size: {real_reach}
Avg Spend: {avg_spent:.2f}
Avg Health Score: {avg_health:.1f}

Based on this, what is your strategy?"""
            }
        ]

        strategy_resp = await call_llm(strategy_prompt, temperature=0.7)
        strategy_data = json.loads(strategy_resp)

        # Fallbacks for safety in case LLM doesn't follow schema perfectly
        target_audience = strategy_data.get("target_audience", "All Customers")
        business_objective = strategy_data.get("business_objective", request.business_goal)
        campaign_concept = strategy_data.get("campaign_concept", "Campaign Concept Details")
        recommended_channel = strategy_data.get("recommended_channel", "email")
        channel_reasoning = strategy_data.get("channel_reasoning", "Best channel for this audience.")
        predicted_open_rate = strategy_data.get("predicted_open_rate", 0.25)
        predicted_ctr = strategy_data.get("predicted_ctr", 0.05)
        predicted_revenue = strategy_data.get("predicted_revenue", 10000.0)
        raw_conf = strategy_data.get("confidence_score", 85)
        try:
            confidence_score = int(float(raw_conf) * 100) if float(raw_conf) <= 1 else int(float(raw_conf))
        except (ValueError, TypeError):
            confidence_score = 85

        # Save segment to DB
        seg_cursor = await db.execute(
            """INSERT INTO segments (name, description, rules_json, customer_count, created_by)
               VALUES (?, ?, ?, ?, 'ai_strategy')""",
            (
                target_audience[:50],
                business_objective,
                json.dumps(filter_json),
                real_reach,
            )
        )
        segment_id = seg_cursor.lastrowid

        # Insert customers into segment_customers
        ids_cursor = await db.execute(f"SELECT id FROM ({sql_query})", params)
        customer_rows = await ids_cursor.fetchall()
        for row in customer_rows:
            await db.execute(
                "INSERT INTO segment_customers (segment_id, customer_id) VALUES (?, ?)",
                (segment_id, row[0])
            )

        await db.commit()

        # Build response
        return AIStrategyResponse(
            business_objective=business_objective,
            target_audience=target_audience,
            audience_filter_json=filter_json,
            estimated_reach=real_reach,
            recommended_channel=recommended_channel,
            channel_reasoning=channel_reasoning,
            campaign_concept=campaign_concept,
            predicted_open_rate=predicted_open_rate,
            predicted_ctr=predicted_ctr,
            predicted_revenue=predicted_revenue,
            confidence_score=confidence_score,
            segment_id=segment_id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e


@router.post("/message")
async def ai_generate_message(request: AIMessageRequest, db: aiosqlite.Connection = Depends(get_db)):
    """Generate message copy based on campaign goal."""
    prompt = [
        {"role": "system", "content": "You are a copywriter. Output JSON: {\"subject_line\": \"...\", \"message\": \"...\", \"channel_recommendation\": \"...\"}"},
        {"role": "user", "content": f"Campaign Goal: {request.campaign_goal}\nTone: {request.tone}\nGenerate a personalized message. Use {{name}} as placeholder."}
    ]
    response = await call_llm(prompt, temperature=0.8)
    return json.loads(response)


@router.post("/analyze", response_model=AICampaignAnalysisResponse)
async def ai_analyze_campaign(request: AICampaignAnalysisRequest, db: aiosqlite.Connection = Depends(get_db)):
    """Post-campaign analysis generator."""
    # Fetch campaign stats
    cursor = await db.execute("SELECT * FROM campaigns WHERE id = ?", (request.campaign_id,))
    campaign = dict(await cursor.fetchone())
    
    prompt = [
        {
            "role": "system",
            "content": """You are an AI Data Analyst. Analyze the campaign results.
Output JSON:
{
  "open_rate_analysis": "...",
  "ctr_analysis": "...",
  "revenue_impact_analysis": "...",
  "key_learnings": ["...", "..."]
}"""
        },
        {
            "role": "user",
            "content": f"Campaign '{campaign['name']}' on {campaign['channel']}.\nSent: {campaign['total_sent']}\nOpened: {campaign['total_opened']}\nClicked: {campaign['total_clicked']}\n\nCRITICAL CONTEXT: Assume an 8.5% conversion rate on all clicked emails, with an Average Order Value of ₹24,500. Calculate the estimated revenue generated and analyze why this campaign succeeded or failed."
        }
    ]
    
    analysis_resp = await call_llm(prompt, temperature=0.5)
    analysis_data = json.loads(analysis_resp)

    # Save to db
    await db.execute(
        "UPDATE campaigns SET post_analysis_json = ? WHERE id = ?",
        (json.dumps(analysis_data), request.campaign_id)
    )
    for learning in analysis_data.get("key_learnings", []):
        await db.execute(
            "INSERT INTO ai_learnings (campaign_id, learning_text, category) VALUES (?, ?, 'analysis')",
            (request.campaign_id, learning)
        )
    await db.commit()

    return AICampaignAnalysisResponse(**analysis_data)
