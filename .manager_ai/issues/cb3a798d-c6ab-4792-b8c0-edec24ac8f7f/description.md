2. main.py:486-492 — CORS allow_credentials=True con allow_origins=["*"]

  allow_origins=["*"],
  allow_credentials=True,
  Combinazione invalida per lo standard CORS. I browser rifiutano richieste con credenziali quando l'origine è wildcard.