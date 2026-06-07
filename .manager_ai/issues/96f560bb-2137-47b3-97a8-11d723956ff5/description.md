1. credential_service.py:17-21 — Chiave Fernet random persa al restart

  key = os.environ.get("MANAGER_AI_SECRET_KEY") or Fernet.generate_key()
  Se MANAGER_AI_SECRET_KEY non è impostata, genera chiave random in memoria. Al restart del server, tutte le credenziali
   diventano permanentemente illeggibili. Deve lanciare errore hard, non degradare silenziosamente.