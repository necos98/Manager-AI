## Piano di implementazione

### Obiettivo
Fixare la race condition nel componente `HermesCommandsPanel` in `routes/settings.tsx` che causa errori console all'apertura/chiusura del terminale nella sezione Settings → Hermes.

### Strategia
Introdurre un `useRef` per tracciare l'ID del terminale attivo, così da evitare stale closure quando `handleSessionEnd` e `handleDialogClose` si sovrappongono. Il ref viene azzerato prima degli state update, garantendo che eventuali callback concorrenti vedano immediatamente lo stato aggiornato.

### Task
1. **Aggiungere `useRef` per terminalId attivo** in `HermesCommandsPanel`
2. **Modificare `handleRun`** per aggiornare il ref insieme allo state
3. **Modificare `handleDialogClose`** per usare il ref come guard
4. **Modificare `handleSessionEnd`** per azzerare il ref prima degli state update
5. **Verificare:** aprire terminale in Settings, lasciare che Hermes command completi, chiudere manualmente, verificare nessun errore console
