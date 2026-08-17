<!-- publicar-repos.md | 13-08-2026 17:40(GMT-04:00) -->

# Publicar Repositórios no GitHub

> **Contexto**: Os diretórios locais não estão conectados ao GitHub (não possuem `origin`). 
> O repositório de contexto na nuvem já foi atualizado via comando do IDE. 
> Os passos abaixo conectam, limpam o histórico antigo na nuvem e publicam o novo estado.

---

## Bloco 1 — Kit: `agente-local-spec-kit`

```bash
cd ~/.vitalia/kit

# 1. Garantir que é um repositório git e conectar à nuvem
git init
git remote remove origin 2>/dev/null || true
git remote add origin git@github.com:vitalia-platform/agente-local-spec-kit.git

# 2. Limpeza do repositório antigo na nuvem (apaga branches extras e tags)
git ls-remote --heads origin | awk '{print $2}' | sed 's/refs\/heads\///' | grep -v 'main' | xargs -r -I {} git push origin --delete {} 2>/dev/null || true
git ls-remote --tags origin | awk '{print $2}' | sed 's/refs\/tags\///' | xargs -r -I {} git push origin --delete {} 2>/dev/null || true

# 3. Criar o commit inicial com o estado atual e enviar (forçando a reescrita do main)
git add .
git commit -m "feat: vitalia kit v0.5.0 — SDD pipeline + grounding guard rails + context engine"
git branch -M main
git push --force origin main
```

---

## Bloco 2 — Projeto: `agente-local`

O projeto já possui repositório Git local, mas não está conectado e o histórico na nuvem precisa ser limpo.

```bash
cd ~/projetos/assistidos/agente-local

# 1. Conectar à nuvem
git remote remove origin 2>/dev/null || true
git remote add origin git@github.com:vitalia-platform/agente-local.git

# 2. Limpeza do repositório antigo na nuvem (apaga branches extras e tags)
git ls-remote --heads origin | awk '{print $2}' | sed 's/refs\/heads\///' | grep -v 'main' | xargs -r -I {} git push origin --delete {} 2>/dev/null || true
git ls-remote --tags origin | awk '{print $2}' | sed 's/refs\/tags\///' | xargs -r -I {} git push origin --delete {} 2>/dev/null || true

# 3. Zerar o histórico local criando uma nova branch órfã
git checkout --orphan temp_branch
git rm -rf --cached .  # Limpa o index herdado para respeitar o .gitignore
git add -A
git commit -m "feat: agente-local v1.0.0 — plataforma vitalia com SDD pipeline completo"

# 4. Substituir a branch antiga pela nova e publicar (forçando a reescrita do main)
git branch -D main 2>/dev/null || true
git branch -m main
git push --force origin main
```

> ⚠️ **Lembrete**: O diretório de contexto `.vitalia/memory/session/` é ignorado pelo `.gitignore` do projeto, o que é o comportamento correto. Ele possui seu próprio pipeline de sincronização (já executado).

---

## Verificação pós-push

```bash
git -C ~/.vitalia/kit log --oneline
git -C ~/projetos/assistidos/agente-local log --oneline
```
