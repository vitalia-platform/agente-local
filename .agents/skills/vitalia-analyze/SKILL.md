---
name: vitalia-analyze
description: >
  Análise read-only de consistência entre spec.md, plan.md e tasks.md. CRITICAL bloqueia /spec-implement. Inclui gates para domínios de saúde e educação.
---
<!-- SKILL.md | Vitalia Kit 0.4.0 — gerado por install-project.sh -->
<!-- Source: /home/andre/.vitalia/kit/extensions/analyze.toml -->

# Vitalia: analyze

Ao acionar este comando:

1. Leia o arquivo `~/.vitalia/kit/extensions/analyze.toml`
2. Extraia o conteúdo do campo `prompt`
3. Execute rigorosamente as instruções do campo `prompt`

> As seções `[meta]`, `[hooks]`, `[tools]`, `[context]`, `[variables]` e
> `[transport]` do arquivo `.toml` são metadados estruturados para orquestradores.
> Como agente Antigravity, use apenas o campo `prompt`.
