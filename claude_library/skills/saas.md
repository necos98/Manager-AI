---
name: saas
category: domain
description: SaaS patterns, multi-tenancy, subscriptions, billing
built_in: true
---
# SaaS Domain Patterns

## Multi-tenancy
- Row-level tenancy: every table has `tenant_id` (or `organization_id`)
- Middleware enforces tenant isolation on every request
- Never expose cross-tenant data in API responses

## Subscriptions & Billing
- Plans: free, starter, pro, enterprise — always extendable
- Subscription state machine: trial → active → past_due → cancelled
- Billing via Stripe: webhook-driven state updates, never trust client
- Metered usage: record events, aggregate on billing cycle

## Onboarding
- Setup wizard captures org name, invites teammates, seeds initial data
- Trial period: 14 days, no credit card required

## Feature Flags
- Gate premium features by subscription plan
- Never hard-code plan checks — use feature flag service
