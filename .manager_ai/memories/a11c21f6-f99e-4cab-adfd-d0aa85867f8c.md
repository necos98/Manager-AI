---
id: a11c21f6-f99e-4cab-adfd-d0aa85867f8c
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: Telegram notifications_enabled toggle — disabilita notifiche dall'UI
parent_id: null
created_at: '2026-06-09T20:48:28.198327+00:00'
updated_at: '2026-06-09T20:48:28.198327+00:00'
links: []
---
TelegramService ora ha un flag _notifications_enabled. is_configured() richiede token + chat_id + enabled=True. Configurabile da UI Settings > Telegram o via API PUT /api/settings/telegram.notifications_enabled. Quando disabilitato, NotificationService (Hermes CLI fallback) riparte automaticamente.