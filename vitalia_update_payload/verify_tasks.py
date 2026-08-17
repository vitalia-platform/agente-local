import os
import re
import json
import requests
from typing import List, Dict

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = "qwen2.5-coder:7b"

def extract_tasks_from_markdown(filepath: str) -> List[Dict[str, str]]:
    """Parse determinístico (Código) para quebrar o tasks.md em tarefas atômicas."""
    tasks = []
    if not os.path.exists(filepath):
        return tasks
    
    with open(filepath, 'r') as f:
        content = f.read()

    # Exemplo simples de RegEx para capturar tarefas no formato T001: [Título] - [Desc]
    matches = re.finditer(r'(T\d{3}):\s*(.*?)(?=\nT\d{3}|$)', content, re.DOTALL)
    for match in matches:
        tasks.append({
            "id": match.group(1),
            "content": match.group(2).strip()
        })
    return tasks

def check_task_with_llm(task: Dict[str, str], rule_text: str) -> bool:
    """Micro-avaliação (1 Tarefa vs 1 Regra) usando LLM-as-a-judge Leve."""
    prompt = f"""
    Você é um juiz de conformidade cirúrgico.
    REGRA DE CONSTITUIÇÃO:
    {rule_text}

    TAREFA PROPOSTA:
    [{task['id']}] {task['content']}

    A Tarefa Proposta viola a Regra de Constituição?
    Responda APENAS com um JSON estrito: {{"violation": true, "reason": "motivo..."}} ou {{"violation": false, "reason": "ok"}}
    """
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "temperature": 0.0
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json().get("response", "{}")
        verdict = json.loads(result)
        return verdict.get("violation", False), verdict.get("reason", "")
    except Exception as e:
        print(f"Erro na inferência do LLM para a tarefa {task['id']}: {e}")
        # Fail-safe: Se o judge falhar, assume true (HITL necessário) ou false dependendo do rigor desejado.
        return True, "Falha de inferência. Revisão humana obrigatória."

def main():
    print("[Task Verifier] Iniciando Verificação Híbrida (Código + LLM)...")
    tasks = extract_tasks_from_markdown(".vitalia/specs/active/tasks.md")
    
    # Simulação de carregamento da constituição (always-on)
    medical_gate_rule = "Nunca permita que uma tarefa implemente lógica clínica de saúde sem revisão de um especialista aprovado."
    
    violations_found = False
    for task in tasks:
        print(f"Checando {task['id']}...")
        is_violating, reason = check_task_with_llm(task, medical_gate_rule)
        if is_violating:
            print(f"⛔ VIOLAÇÃO BLOQUEANTE ({task['id']}): {reason}")
            violations_found = True
        else:
            print(f"✅ {task['id']} aprovada.")
            
    if violations_found:
        print("\n[BLOCKED] O workflow foi interrompido. Corrija o tasks.md antes de rodar /vitalia-spec-implement.")
        exit(1)
    else:
        print("\n[PASS] Todas as tarefas aderem à constituição. Liberado para /vitalia-spec-implement.")
        exit(0)

if __name__ == "__main__":
    main()
