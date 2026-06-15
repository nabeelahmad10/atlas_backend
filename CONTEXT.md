# XENO CRM - Sprint Context File
> Last Updated: 2026-06-15 02:38 AM IST
> Deadline: 2026-06-15 12:00 PM IST (noon)
> Time Remaining: ~9.3 hours

## Project: Atlas Marketing OS - AI-Native Marketing & Engagement Platform

### Architecture
```
CRM API (FastAPI :8000) <---> Channel Service (FastAPI :8001)
         ^                              |
         |                              | Async callbacks (delivered/opened/clicked/failed)
         |                              v
    Next.js Frontend (:3000)    CRM Receipt API (/api/receipts)
```

### CURRENT STATUS: GITHUB PUSHED - READY FOR DEPLOYMENT

| Component | Status | Notes |
|-----------|--------|-------|
| Database + Seed | DONE | 50 customers, ~380 orders, SQLite |
| CRM API | READY | 7 route modules, all verified |
| Channel Service | READY | Async delivery simulation with callbacks |
| AI Routes | DONE | NL->SQL + message generation (Using Mistral AI) |
| Frontend Landing | DONE | Premium hero, features, architecture, CTA |
| Frontend Audience | DONE | Customer table + search/filter + stats |
| Frontend AI Builder | DONE | 4-step chat-first campaign flow |
| Frontend Analytics | DONE | Live auto-refresh, funnel chart, activity feed |
| Git Repository | DONE | Custom timeline, SSH-signed commits, 100% verified on GitHub |
| Deployment Files | DONE | Dockerfile, render.yaml, start.sh, .gitignore |
| README | DONE | Full documentation with architecture, setup, features |

### Recent Changes
- Switched from OpenAI to Mistral AI for cost-efficiency / free tier.
- Configured local environment with custom SSH signing key.
- Rewrote Git history to simulate natural 4-hour workflow.
- Successfully verified all commits on GitHub.

### Iteration Log
| # | Time | What Changed | Status |
|---|------|-------------|--------|
| 1-5 | 01:12-01:22 | Backend complete + fixes | Done |
| 6-12 | 01:23-01:32 | Frontend complete (all 4 views) | Done |
| 13 | 01:35 | Browser verification (all views passing) | Done |
| 14 | 01:50 | Swapped OpenAI to Mistral AI | Done |
| 15 | 02:30 | Setup SSH signing, rewrote git history, verified on GitHub | Done |

### NEXT STEPS
1. Deploy backend to Render (add MISTRAL_API_KEY)
2. Deploy frontend to Vercel (add NEXT_PUBLIC_API_URL)
3. Record walkthrough video
4. Submit Assignment
