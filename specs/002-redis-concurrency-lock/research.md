# Technical Research: Spec 002 — Redis 3-State Concurrency Lock

<!-- research.md | Atualizado em: 28-07-2026 12:51:00(GMT-04:00) -->

---

## Decisão 1: Identificador de Versão do Recurso (`generation_id`)

- **Escolhido**: UUID v7 (string, RFC 9562) via biblioteca `uuid6`
- **Justificativa**: UUID v7 é time-ordered (monotonicamente crescente por design), garantindo zero colisão mesmo em gerações concorrentes sem coordenação central. Elimina o problema ABA sem risco de overflow de integer. A comparação lexicográfica no Lua (`<`) é válida pois o timestamp está na parte mais significativa do UUID v7.
- **Alternativas rejeitadas**:
  - `int` com wrap-around (módulo 2^32): introduz janela ABA no momento exato do overflow após ~4 bilhões de ciclos; rejeitado por segurança.
  - `int` com reset manual + alerting: requer automação adicional de monitoramento; desnecessário dado o custo zero do UUID v7.
  - UUID v4 (aleatório): não é monotônico; comparação lexicográfica não garante ordenação temporal; rejeitado.

---

## Decisão 2: Mecanismo de Entrega de Eventos de Handshake

- **Escolhido**: Redis Streams com `at-least-once delivery` + Consumer Groups
- **Justificativa**: Redis Streams é persistente (sobrevive a crashes do consumer), suporta replay de mensagens (essencial para WSL2 NAT recovery), e Consumer Groups permitem processamento exclusivo por worker. O `at-least-once` é explicitamente necessário dado SC-002 (100% de entrega sob desconexões de 3s).
- **Alternativas rejeitadas**:
  - Redis Pub/Sub: `at-most-once` (mensagem perdida se consumer offline); rejeitado por SC-002.
  - Redis List (`LPUSH`/`BRPOP`): sem Consumer Groups nativos; difícil rastrear ACKs por `event_id`; rejeitado.
  - RabbitMQ: dependência externa desnecessária no hardware atual; rejeitado por YAGNI (Art. XIV).

---

## Decisão 3: Atomicidade das Transições de Estado

- **Escolhido**: Scripts Lua executados no Redis via `EVAL` / `EVALSHA`
- **Justificativa**: Lua scripts no Redis são executados atomicamente — nenhuma outra operação Redis é executada entre o início e o fim do script. Isso garante que verificação de estado + mutação sejam uma operação indivisível, eliminando race conditions sem necessidade de distributed lock externo (que seria circular).
- **Alternativas rejeitadas**:
  - `WATCH` + `MULTI`/`EXEC` (optimistic locking): em carga alta, o WATCH aborta frequentemente, exigindo retry loops; complexidade maior e sem garantia de progresso; rejeitado.
  - `SET NX` (Redis lock simples): não suporta máquina de estados com múltiplos estados válidos; rejeitado.

---

## Decisão 4: Estratégia de Cancelamento de Inferência no Nó 2

- **Escolhido**: `asyncio.Task.cancel()` com `httpx.AsyncClient` no modo `stream=True`
- **Justificativa**: `asyncio.Task.cancel()` injeta `CancelledError` na coroutine alvo na próxima iteração do event loop. Com `stream=True`, a coroutine está em `await response.aiter_bytes()` — um ponto de suspensão, portanto o cancel é processado imediatamente, sem aguardar o payload completo. O teardown do TCP pelo httpx é feito via `response.aclose()` no handler de exceção.
- **Restrição crítica**: O consumer do Redis Stream usa `XREAD BLOCK 50` (50ms máximo). Pior caso de latência: 50ms (poll) + 3ms (HMAC) + 10ms (cancel + event loop) + 15ms (httpx teardown) = **78ms** — bem dentro do SC-003 de 150ms.
- **Alternativas rejeitadas**:
  - `aiohttp` com `session.close()`: equivalente funcional, mas `httpx` já é dependência consolidada no projeto; rejeitado por simplicidade.
  - `httpx` no modo síncrono com thread separada: não integra com asyncio; o cancel não seria propagável; rejeitado.

---

## Decisão 5: Deduplicação de ACK Duplicado (at-least-once redelivery)

- **Escolhido**: Rejeição com código `DUPLICATE_ACK` + log estruturado WARN com delta de tempo
- **Justificativa**: A abordagem de rejeição explícita (opção B do brainstorming) foi preferida porque expõe bugs de configuração de Consumer Group (ex: `XACK` não sendo chamado corretamente após processamento). O delta de tempo entre `timestamp_original` e `timestamp_duplicate` é um sinal diagnóstico valioso para debugging de problemas WSL2 NAT. O set de `event_ids` processados é mantido no Redis com TTL igual ao `timeout_ms` da barreira (5s).
- **Alternativas rejeitadas**:
  - Ignorar silenciosamente: esconde bugs de Consumer Group; rejeitado por observabilidade (Art. XVIII).

---

## Decisão 6: Extensão de TTL da Chave HMAC Durante Lock Ativo

- **Escolhido**: `EXPIRE` embutido no script Lua de consolidação de ACKs
- **Justificativa**: Ao consolidar ACKs, o Lua script já tem acesso atômico ao Redis. Adicionar um `EXPIRE chave:hmac:{session_id} {ttl_extended}` dentro do mesmo script garante que a extensão de TTL e a consolidação de ACKs são operações indivisíveis. Elimina a janela de expiração durante handshake sem chamada extra ao Redis.
- **Alternativas rejeitadas**:
  - Grace period com 2 chaves simultâneas: dobra temporariamente a superfície de ataque; rejeitado por segurança (Art. VII).
  - `EXPIRE` em chamada separada fora do Lua: não atômico; possível race entre expiração e consolidação; rejeitado.

---

## Decisão 7: Framework de Testes

- **Escolhido**: `pytest` + `pytest-asyncio` + `fakeredis[aioredis]` (unit) + Redis real 7.x (integration)
- **Justificativa**: `fakeredis` suporta scripts Lua via `lupa` (Python Lua interpreter), permitindo testar os scripts Lua em isolamento sem Redis real. Testes de integração usam Redis real para validar comportamento de streams, Consumer Groups e TTLs, que `fakeredis` não reproduz perfeitamente.
- **Alternativas rejeitadas**:
  - Apenas `fakeredis` para tudo: não replica comportamento exato de `XREADGROUP`, Consumer Group `PEL` e TTLs; rejeitado.
  - `testcontainers-python` com Redis Docker: overhead de startup alto para unit tests rápidos; reservado para IT apenas se `fakeredis` insuficiente.
