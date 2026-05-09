"""
consultants/ — Gleaning Consultant Pools

Specialist consultants for all three teams.
Loaded from JSON profiles. Available on demand.

Domains:
  food_waste          — food types, waste verification (Gleaning Team)
  data_source         — API health, feed monitoring (Gleaning Team)
  platform_system     — scanner, barter, pawns, map, auth (Gleaning Team)
  community_health    — member trust, onboarding, vulnerable users (Commons Team)
  barter_moderation   — prohibited content, food safety, fairness (Commons Team)
  fund_integrity      — donations, redistribution, operating costs (Commons Team)
  infra_system        — FastAPI, SQLAlchemy, security, merger, performance (Infra Team)
  scanner_health      — HRSA, votes, popup events coverage (Infra Team)
  growth              — resources, pawns, technical debt (Infra Team)
"""

from .pool import ConsultantPool
