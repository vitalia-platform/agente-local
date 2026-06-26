let authToken = null;
let ws = null;

const loginOverlay = document.getElementById('login-overlay');
const dashboardContainer = document.getElementById('dashboard-container');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const wsStatus = document.getElementById('ws-status');

// Login
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = document.getElementById('master-password').value;
    
    try {
        const params = new URLSearchParams();
        params.append('username', 'admin'); // Padrão OAuth2
        params.append('password', password);
        
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params
        });
        
        if (!response.ok) throw new Error('Senha incorreta');
        
        const data = await response.json();
        authToken = data.access_token;
        
        loginOverlay.classList.remove('active');
        loginOverlay.classList.add('hidden');
        dashboardContainer.classList.remove('hidden');
        
        initWebSocket();
        pollGPU();
    } catch (err) {
        loginError.textContent = err.message;
    }
});

// Logout
document.getElementById('btn-logout').addEventListener('click', () => {
    authToken = null;
    if(ws) ws.close();
    dashboardContainer.classList.add('hidden');
    loginOverlay.classList.remove('hidden');
    loginOverlay.classList.add('active');
    document.getElementById('master-password').value = '';
});

// WebSocket
function initWebSocket() {
    // Detecta se é ws:// ou wss://
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/events`);
    
    ws.onopen = () => {
        wsStatus.classList.remove('disconnected');
        wsStatus.classList.add('connected');
    };
    
    ws.onclose = () => {
        wsStatus.classList.remove('connected');
        wsStatus.classList.add('disconnected');
        setTimeout(initWebSocket, 5000); // Tenta reconectar
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            routeEvent(data);
        } catch (e) {
            console.error("Erro no parse WS", e);
        }
    };
}

// Router de Eventos
let totalPrompt = 0;
let totalCompletion = 0;

function routeEvent(event) {
    const { type, source, payload, timestamp } = event;
    const timeStr = new Date(timestamp).toLocaleTimeString();
    let data;
    try { data = typeof payload === 'string' ? JSON.parse(payload) : payload; } 
    catch { data = payload; }

    if (type === 'telemetry') {
        if (data.prompt_tokens) {
            totalPrompt += data.prompt_tokens;
            document.getElementById('stat-prompt').textContent = totalPrompt;
        }
        if (data.completion_tokens) {
            totalCompletion += data.completion_tokens;
            document.getElementById('stat-completion').textContent = totalCompletion;
        }
    } 
    else if (type === 'conversation' || type === 'tool_call') {
        const stream = document.getElementById('chat-stream');
        const div = document.createElement('div');
        div.className = 'msg-item';
        
        let contentStr = '';
        if (type === 'conversation') contentStr = data.text || JSON.stringify(data);
        if (type === 'tool_call') {
            contentStr = "🔧 " + JSON.stringify(data, null, 2);
            div.style.borderLeft = "3px solid var(--neon-yellow)";
        }

        div.innerHTML = `
            <div class="msg-header">
                <span class="msg-source">${source}</span>
                <span>${timeStr}</span>
            </div>
            <div class="msg-content"><pre>${contentStr}</pre></div>
        `;
        stream.appendChild(div);
        stream.scrollTop = stream.scrollHeight;
    }
    else {
        // system_log, reasoning ou outros
        const stream = document.getElementById('log-stream');
        const div = document.createElement('div');
        div.className = `log-item ${type === 'reasoning' ? 'reasoning' : 'system'}`;
        
        let contentStr = typeof data === 'string' ? data : JSON.stringify(data);
        if(data.reasoning) contentStr = data.reasoning;
        if(data.content) contentStr = data.content;

        div.innerHTML = `[${timeStr}] <b>${source}</b> (${type}): <pre class="log-pre">${contentStr}</pre>`;
        stream.appendChild(div);
        stream.scrollTop = stream.scrollHeight;
    }
}

// GPU Polling
async function pollGPU() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/gpu-status');
        if (res.ok) {
            const data = await res.json();
            const container = document.getElementById('gpu-stats-container');
            if (data.error) {
                container.innerHTML = `<p class="error-msg">${data.error}</p>`;
            } else if (data.gpus) {
                container.innerHTML = data.gpus.map(g => `
                    <div style="margin-bottom: 5px;">
                        <span style="font-size: 0.8rem; color: var(--text-secondary)">GPU ${g.gpu_index}</span>
                        <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px; margin-top: 2px;">
                            <div style="background: var(--neon-blue); height: 100%; border-radius: 4px; width: ${(g.used_mb/g.total_mb)*100}%"></div>
                        </div>
                        <span style="font-size: 0.75rem;">${g.used_mb}MB / ${g.total_mb}MB</span>
                    </div>
                `).join('');
            }
        }
    } catch (e) { }
    setTimeout(pollGPU, 10000);
}

// Controle Docker
async function restartContainer(name) {
    const msgBox = document.getElementById('action-msg');
    msgBox.textContent = `Reiniciando ${name}...`;
    try {
        const res = await fetch('/api/control/restart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ container_name: name })
        });
        const data = await res.json();
        if (res.ok) msgBox.textContent = `Sucesso: ${data.message}`;
        else msgBox.textContent = `Erro: ${data.detail}`;
    } catch (e) {
        msgBox.textContent = `Erro de rede: ${e.message}`;
    }
    setTimeout(() => msgBox.textContent = '', 5000);
}

// --------- SETTINGS & BENCHMARK ---------
const settingsOverlay = document.getElementById('settings-overlay');

document.getElementById('btn-open-settings').addEventListener('click', () => {
    if (!authToken) return;
    settingsOverlay.classList.remove('hidden');
    settingsOverlay.classList.add('active');
    loadSettings();
    fetchLLMs();
});

document.getElementById('btn-close-settings').addEventListener('click', () => {
    settingsOverlay.classList.add('hidden');
    settingsOverlay.classList.remove('active');
});

async function loadSettings() {
    try {
        const res = await fetch('/api/settings', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (res.ok) {
            const data = await res.json();
            document.getElementById('env-pubsub').value = data.VITALIA_PUBSUB_ENABLED || '';
            document.getElementById('env-no1').value = data.NO1_LOCAL_OLLAMA_URL || '';
            document.getElementById('env-no2').value = data.NO2_SERVER_IP || '';
        }
    } catch (e) {
        console.error("Erro ao carregar settings", e);
    }
}

document.getElementById('settings-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const msgBox = document.getElementById('settings-msg');
    msgBox.textContent = 'Salvando...';
    
    const settings = {
        VITALIA_PUBSUB_ENABLED: document.getElementById('env-pubsub').value,
        NO1_LOCAL_OLLAMA_URL: document.getElementById('env-no1').value,
        NO2_SERVER_IP: document.getElementById('env-no2').value
    };
    
    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify({ settings })
        });
        if (res.ok) {
            msgBox.textContent = 'Salvo com sucesso! Aplique as mudanças reiniciando os containers necessários.';
            msgBox.style.color = 'var(--neon-green)';
        } else {
            msgBox.textContent = 'Erro ao salvar.';
            msgBox.style.color = 'var(--neon-red)';
        }
    } catch (e) {
        msgBox.textContent = e.message;
    }
});

async function fetchLLMs() {
    try {
        const res = await fetch('/api/llms', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (res.ok) {
            const data = await res.json();
            const select = document.getElementById('benchmark-model');
            select.innerHTML = '';
            
            ['node1', 'node2'].forEach(node => {
                if (data[node] && data[node].length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = node === 'node1' ? 'Nó 1 (Local)' : 'Nó 2 (Server)';
                    data[node].forEach(m => {
                        const opt = document.createElement('option');
                        opt.value = m.name;
                        opt.textContent = m.name;
                        opt.dataset.node = node;
                        optgroup.appendChild(opt);
                    });
                    select.appendChild(optgroup);
                }
            });
            if (select.innerHTML === '') {
                select.innerHTML = '<option value="">Nenhum modelo encontrado</option>';
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Global Benchmark Logic
const benchmarkOverlay = document.getElementById('benchmark-overlay');
const btnOpenGlobal = document.getElementById('btn-open-global-benchmark');
const btnCloseBenchmark = document.getElementById('btn-close-benchmark');
const benchmarkTableBody = document.querySelector('#benchmark-table tbody');
const benchmarkProgress = document.getElementById('benchmark-progress');
const btnApplyBenchmark = document.getElementById('btn-apply-benchmark');

if (btnOpenGlobal) {
    btnOpenGlobal.addEventListener('click', async () => {
        benchmarkOverlay.classList.remove('hidden');
        benchmarkOverlay.classList.add('active');
        await runGlobalBenchmark();
    });
}

if (btnCloseBenchmark) {
    btnCloseBenchmark.addEventListener('click', () => {
        benchmarkOverlay.classList.remove('active');
        benchmarkOverlay.classList.add('hidden');
    });
}

async function runGlobalBenchmark() {
    benchmarkTableBody.innerHTML = '';
    benchmarkProgress.textContent = 'Buscando LLMs disponíveis...';
    btnApplyBenchmark.disabled = true;

    try {
        const res = await fetch('/api/llms', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) throw new Error('Falha ao buscar LLMs');
        const data = await res.json();
        
        const envNo1 = document.getElementById('env-no1').value;
        const envNo2 = document.getElementById('env-no2').value;
        
        let modelsToTest = [];
        if (data.node1) data.node1.forEach(m => modelsToTest.push({ nodeName: 'Nó 1 (Local)', nodeKey: 'node1', url: envNo1, name: m.name }));
        if (data.node2) data.node2.forEach(m => modelsToTest.push({ nodeName: 'Nó 2 (Server)', nodeKey: 'node2', url: envNo2, name: m.name }));
        
        if (modelsToTest.length === 0) {
            benchmarkProgress.textContent = 'Nenhum modelo encontrado para testar.';
            return;
        }

        // Render initial rows
        modelsToTest.forEach((m, idx) => {
            const tr = document.createElement('tr');
            tr.id = `bench-row-${idx}`;
            tr.innerHTML = `
                <td>${m.nodeName}</td>
                <td>${m.name}</td>
                <td class="status">Aguardando...</td>
                <td class="cold-start">-</td>
                <td class="speed">-</td>
                <td>
                    <div class="profile-options" style="display: flex; gap: 8px; font-size: 0.75rem;">
                        <label><input type="checkbox" class="profile-check" value="ROUTER_LLM_PROFILE" data-model="${m.name}" disabled> ROUTER</label>
                        <label><input type="checkbox" class="profile-check" value="DEVELOPER_LLM_PROFILE" data-model="${m.name}" disabled> DEV</label>
                        <label><input type="checkbox" class="profile-check" value="INFRA_LLM_PROFILE" data-model="${m.name}" disabled> INFRA</label>
                        <label><input type="checkbox" class="profile-check" value="REVIEW_LLM_PROFILE" data-model="${m.name}" disabled> REVIEW</label>
                    </div>
                </td>
            `;
            benchmarkTableBody.appendChild(tr);
        });

        // Test sequentially
        for (let i = 0; i < modelsToTest.length; i++) {
            const m = modelsToTest[i];
            const row = document.getElementById(`bench-row-${i}`);
            const statusCell = row.querySelector('.status');
            const coldStartCell = row.querySelector('.cold-start');
            const speedCell = row.querySelector('.speed');
            const checkboxes = row.querySelectorAll('.profile-check');
            
            if (!m.url) {
                statusCell.textContent = 'URL Inválida';
                statusCell.style.color = 'var(--neon-red)';
                continue;
            }

            // Pular modelos de Embedding que não suportam /api/generate
            if (m.name.toLowerCase().includes('embed')) {
                statusCell.textContent = 'Skipped (Embedding)';
                statusCell.style.color = 'var(--text-secondary)';
                coldStartCell.textContent = '-';
                speedCell.textContent = '-';
                checkboxes.forEach(cb => cb.disabled = false);
                continue;
            }

            benchmarkProgress.textContent = `Testando ${m.name} (${i + 1}/${modelsToTest.length})...`;
            statusCell.textContent = 'Running...';
            statusCell.style.color = 'var(--neon-yellow)';
            
            try {
                const bRes = await fetch('/api/benchmark', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ endpoint_url: m.url, model_name: m.name })
                });
                
                const bData = await bRes.json();
                
                if (bRes.ok) {
                    statusCell.textContent = 'Sucesso';
                    statusCell.style.color = 'var(--neon-green)';
                    coldStartCell.textContent = bData.load_duration_ms.toFixed(2);
                    speedCell.textContent = bData.tokens_per_sec.toFixed(2);
                    checkboxes.forEach(cb => cb.disabled = false);
                } else {
                    statusCell.textContent = 'Falha';
                    statusCell.style.color = 'var(--neon-red)';
                    coldStartCell.textContent = bData.detail || 'Erro';
                }
            } catch (err) {
                statusCell.textContent = 'Erro';
                statusCell.style.color = 'var(--neon-red)';
                coldStartCell.textContent = err.message;
            }
        }
        
        benchmarkProgress.textContent = 'Testes concluídos! Assinale os perfis desejados.';
        btnApplyBenchmark.disabled = false;
        
    } catch (e) {
        benchmarkProgress.textContent = `Erro: ${e.message}`;
    }
}

// Aplicar ao Settings (só preenche os inputs do formulário .env no frontend)
btnApplyBenchmark.addEventListener('click', () => {
    const checkedBoxes = document.querySelectorAll('.profile-check:checked');
    let msg = 'Modelos mapeados! (Ainda não salvo)\n\n';
    
    const settingsUpdate = {};
    checkedBoxes.forEach(cb => {
        settingsUpdate[cb.value] = cb.dataset.model;
        msg += `${cb.value} = ${cb.dataset.model}\n`;
    });
    
    if (Object.keys(settingsUpdate).length === 0) {
        alert("Nenhum perfil foi atribuído.");
        return;
    }
    
    fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
        body: JSON.stringify({ settings: settingsUpdate })
    }).then(res => res.json()).then(data => {
        alert("Perfis aplicados ao .env com sucesso!");
        benchmarkOverlay.classList.remove('active');
        benchmarkOverlay.classList.add('hidden');
    }).catch(err => alert("Erro ao salvar perfis: " + err.message));
});
