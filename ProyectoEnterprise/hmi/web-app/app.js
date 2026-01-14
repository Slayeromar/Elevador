/**
 * ENTERPRISE HMI CORE v2.4
 * Industrial Push-Button Logic (Momentary Contact)
 */

console.log("🚀 [HMI] Iniciando carga de scripts v2.4...");

const getHostname = () => {
    const hn = window.location.hostname;
    return (hn === '0.0.0.0' || hn === '') ? 'localhost' : hn;
};

const CONFIG = {
    GATEWAY_URL: `http://${getHostname()}:8080`,
    WS_URL: `ws://${getHostname()}:8080/ws/telemetry`,
    ALARM_POLL_INTERVAL: 2000,
    AI_POLL_INTERVAL: 5000
};

// Global State
let authToken = localStorage.getItem('ent_token');
let systemIntervals = [];
let isRequesting = false;
let socket = null;

// UI References
let car, motorLabel, statusPill, cycleTimeDisplay, mTemp, loginScreen, loginError;
let tags = {}, lamps = {};

/**
 * Initialize UI elements after DOM is loaded
 */
function initUI() {
    console.log("📦 [HMI] Inicializando referencias UI...");

    car = document.getElementById('elevator-car');
    motorLabel = document.getElementById('motor-label');
    statusPill = document.getElementById('status-pill');
    cycleTimeDisplay = document.getElementById('cycle-time');
    mTemp = document.getElementById('m-temp');
    loginScreen = document.getElementById('login-screen');
    loginError = document.getElementById('login-error');

    tags = {
        bp1: document.getElementById('tag-bp1'),
        bp2: document.getElementById('tag-bp2'),
        ls1: document.getElementById('tag-ls1'),
        ls2: document.getElementById('tag-ls2'),
        mc1: document.getElementById('tag-mc1'),
        mc2: document.getElementById('tag-mc2')
    };

    lamps = {
        l1: document.getElementById('lamp-l1'),
        l2: document.getElementById('lamp-l2')
    };

    // Attach primary events
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('btn-logout').addEventListener('click', logout);

    // INDUSTRIAL PUSH-BUTTON LOGIC (TIA Portal Style)
    setupIndustrialButton('btn-up', 'bp1');
    setupIndustrialButton('btn-down', 'bp2');

    // Fault Injection
    document.getElementById('btn-fault-jam').addEventListener('click', () => injectFault('jam'));
    document.getElementById('btn-fault-reset').addEventListener('click', () => injectFault('reset'));

    // Logs
    document.getElementById('btn-open-logs').addEventListener('click', openLogs);
    document.getElementById('btn-close-logs').addEventListener('click', () => { document.getElementById('logs-modal').style.display = 'none'; });

    console.log("✅ [HMI] UI Lista con lógica de pulsadores.");
    validateAndStart();
}

/**
 * Robust Button Controller (Momentary Contact)
 */
function setupIndustrialButton(id, tagName) {
    const btn = document.getElementById(id);
    if (!btn) return;

    // We use a local state to prevent multiple rapid triggers
    let isPressed = false;

    const startAction = (e) => {
        if (isPressed) return;
        isPressed = true;
        if (e.cancelable) e.preventDefault();

        btn.style.transform = "scale(0.95)";
        btn.style.filter = "brightness(0.9)";

        console.log(`🔘 [IO] Input High: ${tagName}`);
        sendCommand(tagName, true);
    };

    const stopAction = (e) => {
        if (!isPressed) return;
        isPressed = false;
        if (e && e.cancelable) e.preventDefault();

        btn.style.transform = "scale(1)";
        btn.style.filter = "brightness(1)";

        console.log(`⚪ [IO] Input Low: ${tagName}`);
        sendCommand(tagName, false);
    };

    // Desktop Events
    btn.addEventListener('mousedown', startAction);
    window.addEventListener('mouseup', (e) => { if (isPressed) stopAction(e); }); // Window level for safety
    btn.addEventListener('mouseleave', stopAction);

    // Mobile/Touch Events
    btn.addEventListener('touchstart', startAction, { passive: false });
    btn.addEventListener('touchend', stopAction, { passive: false });
    btn.addEventListener('touchcancel', stopAction);
}

/**
 * Handle Login Form Submission
 */
async function handleLogin(e) {
    e.preventDefault();
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;

    loginError.textContent = 'Autenticando...';
    try {
        const formData = new URLSearchParams();
        formData.append('username', u);
        formData.append('password', p);

        const response = await fetch(`${CONFIG.GATEWAY_URL}/auth/token`, {
            method: 'POST',
            body: formData,
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });

        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            localStorage.setItem('ent_token', authToken);
            await validateAndStart();
        } else {
            const errorData = await response.json().catch(() => ({ detail: 'Acceso denegado' }));
            loginError.textContent = errorData.detail;
        }
    } catch (err) {
        loginError.textContent = 'Gateway inalcanzable (Check 8080)';
    }
}

async function validateAndStart() {
    if (!authToken) {
        loginScreen.style.display = 'flex';
        return;
    }

    try {
        const response = await fetch(`${CONFIG.GATEWAY_URL}/auth/users/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const user = await response.json();
            loginScreen.style.opacity = '0';
            setTimeout(() => {
                loginScreen.style.display = 'none';
                loginScreen.style.opacity = '1';
            }, 500);

            document.getElementById('chaos-panel').style.display = user.role === 'admin' ? 'block' : 'none';
            startSystem();
        } else {
            logout();
        }
    } catch (err) {
        loginScreen.style.display = 'flex';
    }
}

function logout() {
    localStorage.removeItem('ent_token');
    authToken = null;
    systemIntervals.forEach(clearInterval);
    if (socket) socket.close();
    loginScreen.style.display = 'flex';
}

/**
 * Real-time Connection
 */
function connectWS() {
    if (socket) socket.close();
    socket = new WebSocket(CONFIG.WS_URL);

    socket.onopen = () => {
        statusPill.className = 'status-pill online';
        statusPill.textContent = 'SISTEMA ONLINE';
    };

    socket.onmessage = (event) => {
        try {
            const payload = JSON.parse(event.data);
            if (payload.event === "machine.state.changed") {
                updateHMI(payload.data);
            }
        } catch (e) { }
    };

    socket.onclose = () => {
        statusPill.className = 'status-pill offline';
        statusPill.textContent = 'RECONECTANDO...';
        setTimeout(connectWS, 4000);
    };
}

async function sendCommand(btn, val) {
    try {
        await fetch(`${CONFIG.GATEWAY_URL}/plc/command/${btn}?value=${val}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
    } catch (e) { console.error("IO Error:", e); }
}

async function injectFault(type) {
    try {
        await fetch(`${CONFIG.GATEWAY_URL}/plc/simulate/inject-fault/${type}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
    } catch (e) { }
}

function updateHMI(d) {
    const start = performance.now();

    if (d.pos !== undefined) {
        car.style.bottom = `${d.pos * 270}px`; // Ajustado para que no sobrepase el techo del edificio
        mTemp.textContent = (24 + (d.pos * 5)).toFixed(1) + "°C";
    }

    if (!d.mc1 && !d.mc2 && (d.ls1 || d.ls2)) car.classList.add('doors-open');
    else car.classList.remove('doors-open');

    if (d.mc1) motorLabel.textContent = 'SUBIENDO';
    else if (d.mc2) motorLabel.textContent = 'BAJANDO';
    else motorLabel.textContent = 'IDLE';

    if (lamps.l1) lamps.l1.classList.toggle('active', d.l1);
    if (lamps.l2) lamps.l2.classList.toggle('active', d.l2);

    cycleTimeDisplay.textContent = Math.round(performance.now() - start);
    Object.keys(tags).forEach(k => {
        if (d[k] !== undefined && tags[k]) {
            const el = tags[k];
            const label = el.querySelector('.tag-status');
            if (d[k]) { el.classList.add('active'); if (label) label.textContent = 'ACTIVO'; }
            else { el.classList.remove('active'); if (label) label.textContent = 'INACTIVO'; }
        }
    });
}

/**
 * Monitoring Cycles
 */
async function fetchAlarms() {
    if (!authToken) return;
    try {
        const r = await fetch(`${CONFIG.GATEWAY_URL}/alarms/alarms/active`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (r.ok) {
            const data = await r.json();
            const list = document.getElementById('active-alarms-list');
            if (data.length === 0) {
                list.innerHTML = '<div style="color:#10b981; font-weight:700;">🟢 SISTEMA INTEGRAL OK</div>';
            } else {
                list.innerHTML = data.map(a => `
                    <div style="background:#fee2e2; border-left:4px solid #ef4444; padding:10px; margin-bottom:10px; border-radius:8px; font-size:0.75rem;">
                        <b style="color:#b91c1c;">[${a.code}]</b><br>
                        <span>${a.message}</span>
                    </div>
                `).join('');
            }
        }
    } catch (e) { }
}

async function fetchAIInsights() {
    try {
        const response = await fetch(`${CONFIG.GATEWAY_URL}/ai/insights`);
        if (!response.ok) return;
        const data = await response.json();
        const hc = document.getElementById('ai-health-circle');
        const it = document.getElementById('ai-insight-text');
        const at = document.getElementById('ai-avg-time');
        if (hc) hc.textContent = data.health_score;
        if (it) it.textContent = data.insights;
        if (at) at.textContent = data.avg_travel_time;
    } catch (e) { }
}

async function openLogs() {
    document.getElementById('logs-modal').style.display = 'flex';
    document.getElementById('full-history-list').innerHTML = 'Cargando historial...';
    try {
        const r = await fetch(`${CONFIG.GATEWAY_URL}/alarms/alarms/history`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const h = await r.json();
        document.getElementById('full-history-list').innerHTML = h.map(x => `
            <div style="font-size:0.75rem; border-bottom:1px solid #eee; padding:8px; display:flex; gap:10px;">
                <span style="color:#94a3b8; flex-shrink:0;">${new Date(x.timestamp).toLocaleTimeString()}</span>
                <b style="color:#ef4444; min-width:80px;">${x.code}</b>
                <span style="color:#475569;">${x.message}</span>
            </div>
        `).join('') || 'Sin registros.';
    } catch (e) {
        document.getElementById('full-history-list').innerHTML = 'Error.';
    }
}

function startSystem() {
    systemIntervals.forEach(clearInterval);
    systemIntervals = [
        setInterval(() => { const c = document.getElementById('live-clock'); if (c) c.textContent = new Date().toLocaleTimeString(); }, 1000),
        setInterval(fetchAlarms, CONFIG.ALARM_POLL_INTERVAL),
        setInterval(fetchAIInsights, CONFIG.AI_POLL_INTERVAL)
    ];
    connectWS();
}

// Start sequence
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUI);
} else {
    initUI();
}
