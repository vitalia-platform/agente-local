# telemetry_api.py | Atualizado em: 26-06-2026 12:08:18(GMT-04:00)
import os
import subprocess
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

app = FastAPI(title="Vitalia Telemetry API")

@app.get("/gpu-status")
def get_gpu_status():
    """Retorna o estado da VRAM usando nvidia-smi, para monitoramento do Nó 2."""
    try:
        # Pega a memória total, livre e usada da GPU (em MiB)
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.free,memory.used", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            return {"error": "nvidia-smi falhou", "details": result.stderr.strip()}
            
        lines = result.stdout.strip().split('\n')
        gpus = []
        
        for idx, line in enumerate(lines):
            parts = line.split(',')
            if len(parts) >= 3:
                free_mb = int(parts[1].strip())
                gpus.append({
                    "gpu_index": idx,
                    "total_mb": int(parts[0].strip()),
                    "free_mb": free_mb,
                    "used_mb": int(parts[2].strip()),
                    "status": "healthy" if free_mb > 500 else "warning_oom_risk"
                })
                
        return {"gpus": gpus}
    except FileNotFoundError:
        return {"error": "Comando nvidia-smi não encontrado. Driver NVIDIA ausente?"}
    except Exception as e:
        return {"error": f"Erro interno: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
