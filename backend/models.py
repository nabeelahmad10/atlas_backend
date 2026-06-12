"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Customer Models ───────────────────────────────────────────

class CustomerBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    joined_at: str
    total_spent: float
    total_orders: int
    last_order_date: Optional[str] = None
    tags: str = "[]"

class CustomerDetail(CustomerResponse):
    orders: List[dict] = []


# ─── Order Models ──────────────────────────────────────────────

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    product_name: str
    category: str
    amount: float
    quantity: int
    ordered_at: str


# ─── Segment Models ───────────────────────────────────────────

class SegmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rules_json: str = "{}"
    customer_ids: List[int] = []

class SegmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    rules_json: str
    customer_count: int
    created_by: str
    created_at: str


# ─── Campaign Models ──────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str
    segment_id: int
    message_template: str
    channel: str = "email"

class CampaignResponse(BaseModel):
    id: int
    name: str
    segment_id: int
    message_template: str
    channel: str
    status: str
    total_sent: int
    total_delivered: int
    total_failed: int
    total_opened: int
    total_clicked: int
    sent_at: Optional[str] = None
    created_at: str


# ─── AI Models ─────────────────────────────────────────────────

class AISegmentRequest(BaseModel):
    prompt: str = Field(..., description="Natural language query to segment customers")

class AISegmentResponse(BaseModel):
    segment_name: str
    description: str
    filter_json: dict
    customer_count: int
    customer_ids: List[int]
    segment_id: int

class AIMessageRequest(BaseModel):
    segment_id: int
    campaign_goal: str = Field(..., description="What is the goal of this campaign?")
    tone: str = "friendly"

class AIMessageResponse(BaseModel):
    message: str
    subject_line: Optional[str] = None
    channel_recommendation: str

class AIStrategyRequest(BaseModel):
    business_goal: str = Field(..., description="The marketing outcome you want to achieve.")

class AIStrategyResponse(BaseModel):
    business_objective: str
    target_audience: str
    audience_filter_json: dict
    estimated_reach: int
    recommended_channel: str
    channel_reasoning: str
    campaign_concept: str
    predicted_open_rate: float
    predicted_ctr: float
    predicted_revenue: float
    confidence_score: int
    segment_id: int

class AICampaignAnalysisRequest(BaseModel):
    campaign_id: int

class AICampaignAnalysisResponse(BaseModel):
    open_rate_analysis: str
    ctr_analysis: str
    revenue_impact_analysis: str
    key_learnings: List[str]

# ─── Receipt & Event Models ───────────────────────────────────

class DeliveryReceipt(BaseModel):
    communication_id: int
    status: str  # delivered, failed, opened, clicked
    timestamp: str
    failure_reason: Optional[str] = None


# ─── Analytics Models ─────────────────────────────────────────

class CampaignAnalytics(BaseModel):
    campaign_id: int
    campaign_name: str
    channel: str
    total_sent: int
    total_delivered: int
    total_failed: int
    total_opened: int
    total_clicked: int
    delivery_rate: float
    open_rate: float
    click_rate: float

class OverallAnalytics(BaseModel):
    total_campaigns: int
    total_messages_sent: int
    avg_delivery_rate: float
    avg_open_rate: float
    avg_click_rate: float
    campaigns: List[CampaignAnalytics]
