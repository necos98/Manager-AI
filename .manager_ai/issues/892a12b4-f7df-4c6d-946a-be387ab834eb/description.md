Il TTL del `ReadCache` è 30 secondi (`cache.py:12`). La motivazione originale era "safety net for external file modifications not caught by watcher". Ma:
1. Il watcher fa già `.clear()` su qualsiasi modifica — il TTL non è il meccanismo primario di invalidazione
2. 30s è così breve che causa cache miss frequenti anche durante la navigazione normale
3. Con invalidation coarse-grained (`.clear()`), un TTL più lungo non peggiora la consistenza

**Proposta:** Alzare a 300s (5 minuti) o rimuovere completamente il TTL. La cache è in-process, quindi non ha problemi di memoria condivisa. L'unico rischio è una modifica esterna non catturata dal watcher, che è un edge case raro.

**File:** `backend/app/storage/cache.py:12` — `def __init__(self, ttl: float = 30.0)`