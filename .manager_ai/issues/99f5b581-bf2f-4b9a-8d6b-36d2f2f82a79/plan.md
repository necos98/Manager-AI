# Implementation Plan: MySQL Read-Only MCP Plugin

## Overview

Aggiungere il manifest `backend/plugins/mysql/plugin.yaml` al catalogo built-in. Nessun codice richiesto.

## Files

- **Create:** `backend/plugins/mysql/plugin.yaml` — manifest dichiarativo del plugin

## Task 1: Creare il manifest del plugin MySQL

**File:** Crea `backend/plugins/mysql/plugin.yaml`

Il manifest definisce il plugin MySQL read-only con:
- Transport stdio via `uvx mcp-server-mysql`
- Access level `read_only`
- 5 opzioni di configurazione: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

### Step 1: Creare la directory e il file plugin.yaml

```bash
New-Item -ItemType Directory -Force -Path "backend/plugins/mysql"
```

### Step 2: Scrivere il manifest

```yaml
name: "MySQL Database"
description: "Read-only SQL queries and schema inspection on MySQL databases"
transport: stdio
command: "uvx"
args:
  - "mcp-server-mysql"
access_level: read_only
timeout: 30
options:
  - key: MYSQL_HOST
    label: "Host"
    type: string
    required: true
    placeholder: "localhost"
  - key: MYSQL_PORT
    label: "Port"
    type: string
    required: false
    default: "3306"
  - key: MYSQL_USER
    label: "Username"
    type: string
    required: true
  - key: MYSQL_PASSWORD
    label: "Password"
    type: secret
    required: true
  - key: MYSQL_DATABASE
    label: "Database"
    type: string
    required: true
    placeholder: "my_database"
```

### Step 3: Verifica

Riavviare il backend e verificare nel log che `CatalogLoader` carichi il plugin senza errori.

```bash
python start.py
```

Expected: log mostra `Loaded catalog plugin: mysql` senza warning.

### Step 4: Commit

```bash
git add backend/plugins/mysql/plugin.yaml
git commit -m "feat: add MySQL read-only plugin to catalog"
```