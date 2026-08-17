# Quickstart: Context Refactor — Validação End-to-End

**Spec**: [spec.md](./spec.md)  
**Date**: 30-07-2026

---

## Pré-requisitos

- Python 3.8+ com PyYAML: `pip install pyyaml`
- Sub-repositório Git configurado em `.vitalia/memory/session/` com remote origin
- Variável de ambiente: `HOSTNAME` disponível

---

## Cenário 1: Session-start em projeto novo (SC-005)

**Mapeia**: US-005

```bash
# Simular projeto novo removendo data/
rm -rf .vitalia/memory/session/data/
# Acionar session-start
# → Agente chama: python3 .vitalia/scripts/vitalia_context_engine.py --action init
```

**Esperado**:
- Diretório `data/` criado com `learnings.jsonl`, `decisions.jsonl`, `session_history.jsonl` vazios
- `machines.json` criado com estrutura `{"machines": {}}`
- Agente exibe: "Nenhum contexto anterior encontrado. Projeto iniciado."

---

## Cenário 2: Session-end não contamina a raiz (SC-001)

**Mapeia**: US-001

```bash
# Verificar estado antes
git -C .vitalia/memory/session status

# Acionar session-end
# → Agente escreve shards/local.yaml e data/session_history.jsonl

# Verificar que raiz não foi modificada
git -C .vitalia/memory/session diff -- LEARNINGS.md DECISIONS.md SESSION_STATE.md
```

**Esperado**:
- `git diff` retorna vazio para os arquivos raiz
- Apenas `shards/local.yaml`, `data/machines.json`, `data/session_history.jsonl` modificados

---

## Cenário 3: session-consolidate completo com push (SC-002 + SC-007)

**Mapeia**: US-001, US-004

```bash
# Acionar session-consolidate
# → git pull --rebase
# → python3 .vitalia/scripts/vitalia_context_engine.py --action consolidate
# → LLM merge de decisions.jsonl
# → git commit + git push
```

**Esperado**:
- `DASHBOARD.md` gerado com status de semáforo LIVRE
- `LEARNINGS.md`, `DECISIONS.md`, `SESSION_HISTORY.md` regerados
- Log exibe contagem de entradas novas vs ignoradas (deduplicadas)
- `git push` bem-sucedido ou mensagem HITL com comando manual

---

## Cenário 4: Migração de histórico legado (SC-008)

**Mapeia**: FR-012

```bash
# Executar migração
python3 .vitalia/scripts/vitalia_context_engine.py --action migrate \
  --session-dir .vitalia/memory/session

# Verificar resultado
ls .vitalia/memory/session/data/
# → learnings.jsonl decisions.jsonl session_history.jsonl machines.json
ls .vitalia/memory/session/*.bak 2>/dev/null
# → LEARNINGS.md.bak DECISIONS.md.bak (se existiam)
head -3 .vitalia/memory/session/data/learnings.jsonl
# → {"id":"...","ts":"...","ts_confidence":"estimated","machine_id":"pre-migration",...}
```

**Esperado**:
- Todos os `.md` legados convertidos para JSONL
- Arquivos `.md.bak` presentes como backup
- Views `.md` regeradas a partir do JSONL
