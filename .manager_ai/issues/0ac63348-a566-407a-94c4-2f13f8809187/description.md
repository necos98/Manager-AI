Sostituire l'attuale sistema di notifiche Telegram, che funziona spawnando una CLI di Hermes con un testo e sperando che Hermes lo prenda in carico e invii la notifica, con un sistema che integri direttamente le Telegram Bot API.

Problemi dell'approccio attuale:
- Difficile da debuggare: non si sa cosa Hermes combini internamente
- Può fallire silenziosamente senza che l'utente riceva la notifica
- Dipendenza dal provider Hermes e dal suo stato in quel momento
- Nessun controllo diretto sul flusso di invio

Richiesta:
- Integrare le Telegram API direttamente (python-telegram-bot o httpx chiamate dirette all'API Bot)
- Il bot deve poter comunicare con un bot Telegram specifico del progetto
- Le notifiche devono essere inviate direttamente, senza passare per Hermes CLI
- Deve essere più resiliente e tracciabile rispetto all'attuale sistema

L'utente deve poter configurare l'api-key del bot all'interno della sezione "Settings" > "Telegram", dove l'utente può attivare le notifiche tramite un toggle e poi può configurare l'api-key.

Il progetto ha già un bot Telegram configurato? Se sì, usare il token esistente. Se no, prevedere la configurazione di un bot Telegram per le notifiche.