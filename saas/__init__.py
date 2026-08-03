"""Multi-tenant SaaS layer for the Bulk Gmail Mailer.

This package turns the single-user mailer into a hosted, multi-tenant web
product: user accounts, per-user campaign isolation, subscription tiers with
usage limits, a dashboard, and a marketing/pricing site. It reuses the core
engine in ``src`` (template rendering, HTML→PPTX, message building).
"""
