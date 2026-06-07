 21. plugin_client.py:281-300 — Leak processi zombie

  _exit_transport() ha timeout di 3s/5s. Se timeout superati, il processo rimane zombie senza kill esplicito.