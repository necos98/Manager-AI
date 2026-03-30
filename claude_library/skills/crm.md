---
name: crm
category: domain
description: CRM domain patterns, contact management, pipeline, integrations
built_in: true
---
# CRM Domain Patterns

## Core Entities
- Contact (person), Account (company), Deal (opportunity)
- Activities: call, email, meeting — always linked to Contact or Deal
- Pipeline: stages with probability, expected close date

## Business Rules
- A Contact belongs to at most one Account (B2B CRM)
- Deals move through pipeline stages, never skip backward
- All activities must be logged — never delete, only mark completed/cancelled
- Duplicate detection on email and phone before creating Contact

## Integrations
- Email sync: always use IMAP/SMTP, store sent emails as Activities
- Calendar sync: bidirectional, avoid event duplication
- Webhooks for outbound notifications on stage changes

## Reporting
- Conversion rate = Deals won / Deals created in period
- Average deal cycle = days from creation to close
- Funnel view by stage counts and values
