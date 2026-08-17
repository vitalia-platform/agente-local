# Data Model: Context Refactor — JSONL, Semáforo e Workflows

**Spec**: [spec.md](./spec.md)  
**Date**: 30-07-2026

---

## Entidade: JSONL Entry (Learnings / Decisions / Session History)

Formato de uma linha no arquivo `.jsonl`:

```json
{
  "id":            "string[16]",
  "ts":            "string (ISO 8601 com offset, ex: 2026-07-30T16:31:11-04:00)",
  "ts_confidence": "exact | estimated",
  "machine":       "string (nome legível, ex: 'Server GTX 1060')",
  "machine_id":    "string (8 chars hex | 'pre-migration')",
  "category":      "[KIT] | [PROJETO] | [DECISÃO] | [SESSÃO]",
  "content":       "string"
}
```

**Geração do `id`**:
```python
import hashlib
id = hashlib.sha256(f"{category}{content[:128]}".encode()).hexdigest()[:16]
```

**Ciclo de vida**:
- Criado por `session-end` (session_history) ou `session-consolidate` (learnings, decisions)
- Nunca modificado (imutável)
- Deduplicado por `id` no merge

---

## Entidade: Shard (por máquina)

Arquivo: `shards/<machine_id>.yaml`

```yaml
machine: "local"              # nome legível
machine_id: "e55b4d1f"        # sha256(hostname)[:8]
last_sync: "2026-07-30T16:31:11-04:00"
status: "Concluído"           # Concluído | Em andamento | Parado
task: "descrição da tarefa"
p0: "próximo passo desta máquina"
```

**Ciclo de vida**:
- Criado/sobrescrito pelo `session-end` (nunca append)
- Lido pelo `session-consolidate` e `session-start` (via engine)
- Um arquivo por máquina; machine_id é a chave natural

---

## Entidade: machines.json

Arquivo: `data/machines.json`

```json
{
  "machines": {
    "e55b4d1f": {
      "name": "local",
      "first_seen": "2026-07-28T16:31:11-04:00",
      "last_seen": "2026-07-30T16:31:11-04:00"
    },
    "a1b2c3d4": {
      "name": "Server GTX 1060",
      "first_seen": "2026-06-25T10:39:47-04:00",
      "last_seen": "2026-07-01T15:03:00-04:00"
    }
  }
}
```

**Ciclo de vida**:
- Upsert por `machine_id` pelo `session-end`
- `first_seen`: setado apenas na primeira inserção
- `last_seen`: atualizado a cada `session-end`

---

## Entidade: Semáforo (seção do DASHBOARD.md)

Seção no arquivo `DASHBOARD.md` (gerado):

```markdown
## 🔒 Status de Consolidação

| Campo | Valor |
|---|---|
| **Status** | LIVRE |
| **Máquina** | — |
| **Desde** | — |
| **Expira em** | — |
```

Quando bloqueado:

```markdown
## 🔒 Status de Consolidação

| Campo | Valor |
|---|---|
| **Status** | ⚠️ LOCKED |
| **Máquina** | local (e55b4d1f) |
| **Desde** | 2026-07-30T16:31:11-04:00 |
| **Expira em** | 2026-07-30T16:41:11-04:00 |
```

**Ciclo de vida**:
- LIVRE → LOCKED: no início do `session-consolidate` (após `git pull --rebase` com sucesso)
- LOCKED → LIVRE: incluído no commit de consolidação (push bem-sucedido revela LIVRE)
- LOCKED expirado (> 10 min desde `Expira em`): ignorado pela próxima máquina

---

## Relacionamentos

```
machines.json (registry)
    ↑ upsert por session-end
    
shards/<machine_id>.yaml (estado atual da máquina)
    ↑ sobrescrito por session-end
    ↓ lido por session-consolidate → alimenta DASHBOARD.md + SESSION_STATE.md

data/learnings.jsonl  ←── append por session-consolidate (de learnings no shard)
data/decisions.jsonl  ←── append por session-consolidate (de decisions no shard)
data/session_history.jsonl ←── append por session-end (uma entrada por sessão)

Views geradas (somente leitura para agente):
  LEARNINGS.md   ← de learnings.jsonl
  DECISIONS.md   ← de decisions.jsonl
  SESSION_HISTORY.md ← de session_history.jsonl
  SESSION_STATE.md   ← de shards + data/
  DASHBOARD.md       ← de shards + machines.json + semáforo
```
