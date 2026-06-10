## Sostituire confirm() nativo con Dialog Radix

**Problema:** confirm('Terminare questo terminale?') usa dialog nativo browser, brutto.

**Obiettivo:** Usare Dialog Radix UI come gia fatto per delete issue.

**Cosa fare:**
1. Sostituire confirm() in terminals.tsx con Dialog Radix
2. Stesso pattern di delete confirmation dialog