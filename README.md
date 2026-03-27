# 🤖 ManagerAI

> Automazione intelligente dei tuoi progetti con Claude AI integrato.

---

## 🚀 Avvio rapido

### 1. Avvia l'applicazione

**Windows** — fai doppio clic su **`start.bat`**, oppure da terminale:

```bat
start.bat
```

**Linux/macOS** — da terminale:

```bash
chmod +x start.sh   # solo la prima volta
./start.sh
```

Attendi il completamento dell'installazione automatica delle dipendenze.

---

## ⚙️ Configurazione iniziale

### 2. Configura il terminale integrato

Al primo avvio, vai in **`Settings`** → **`Terminal`** e aggiungi il seguente comando:

```
claude "/run-issue $issue_id" --dangerously-skip-permissions
```

---

## 📦 Setup del progetto

### 3. Crea il tuo progetto

Crea un nuovo progetto dall'interfaccia principale.

### 4. Installa le risorse necessarie

Vai nella sezione **`Summary`** ed esegui nell'ordine:

1. Clicca **`Install manager.json`**
2. Clicca **`Install Claude Resources`**
3. Clicca **`MCP Setup`**

### 5. Collega il server MCP

Dopo aver cliccato su **`MCP Setup`**, copia il comando mostrato:

```bash
claude mcp add --transport http ManagerAi http://localhost:8000/mcp/
```

Aprì la **CLI del tuo progetto**, incolla il comando e premi invio.

> 💡 **Nota:** Questa procedura verrà automatizzata nelle versioni future.

---

## 📋 Riepilogo passaggi

| # | Step | Dove |
|---|------|------|
| 1 | Avvia `start.bat` (Win) / `start.sh` (Linux) | Root del progetto |
| 2 | Aggiungi comando al terminale | `Settings` → `Terminal` |
| 3 | Crea il progetto | Interfaccia principale |
| 4 | Install `manager.json` | `Summary` |
| 5 | Install Claude Resources | `Summary` |
| 6 | MCP Setup + CLI | `Summary` → CLI progetto |

---

## 🛠️ Requisiti

- Windows (per `start.bat`) o Linux/macOS (per `start.sh`)
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code/overview) installato e configurato
- Connessione internet per il download delle dipendenze

---

## 📄 Licenza

Distribuito sotto licenza MIT. Vedi `LICENSE` per maggiori informazioni.
