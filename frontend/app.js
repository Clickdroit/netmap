// Net-Map Application Controller v1.2

let networkGraph = null;
let networkData = { nodes: new vis.DataSet([]), edges: new vis.DataSet([]) };
let allDevices = [];
let defaultNetwork = null;
let socket = null;
let currentLayout = 'physics'; // 'physics', 'tree', 'radial'
let isMonitoring = false;
let currentSelectedDevice = null;
let alertCount = 0;

// DOM Elements
const navSubnet = document.getElementById('nav-subnet');
const navGateway = document.getElementById('nav-gateway');
const navLocalIp = document.getElementById('nav-local-ip');

const btnStartScan = document.getElementById('btn-start-scan');
const scanBtnText = document.getElementById('scan-btn-text');
const scanIcon = document.getElementById('scan-icon');

const scanBanner = document.getElementById('scan-banner');
const bannerMessage = document.getElementById('banner-message');
const bannerDetail = document.getElementById('banner-detail');
const progressFill = document.getElementById('progress-fill');
const progressPercent = document.getElementById('progress-percent');

const statTotal = document.getElementById('stat-total');
const statPcs = document.getElementById('stat-pcs');
const statMobiles = document.getElementById('stat-mobiles');
const statIot = document.getElementById('stat-iot');

const tabMapBtn = document.getElementById('tab-map-btn');
const tabTableBtn = document.getElementById('tab-table-btn');
const viewMap = document.getElementById('view-map');
const viewTable = document.getElementById('view-table');
const tabCountBadge = document.getElementById('tab-count-badge');
const graphContainer = document.getElementById('network-graph');
const graphPlaceholder = document.getElementById('graph-placeholder');

// Layout Buttons
const btnLayoutPhysics = document.getElementById('btn-layout-physics');
const btnLayoutTree = document.getElementById('btn-layout-tree');
const btnLayoutRadial = document.getElementById('btn-layout-radial');
const btnFitMap = document.getElementById('btn-fit-map');

// Surveillance & Alerts
const btnToggleMonitor = document.getElementById('btn-toggle-monitor');
const monitorDot = document.getElementById('monitor-dot');
const monitorStatusText = document.getElementById('monitor-status-text');
const btnAlerts = document.getElementById('btn-alerts');
const alertsBadge = document.getElementById('alerts-badge');
const alertsModal = document.getElementById('alerts-modal');
const alertsContainer = document.getElementById('alerts-container');
const btnCloseAlerts = document.getElementById('btn-close-alerts');
const btnDismissAlerts = document.getElementById('btn-dismiss-alerts');
const btnClearAlerts = document.getElementById('btn-clear-alerts');

// Table & Search
const searchInput = document.getElementById('search-input');
const deviceTableBody = document.getElementById('device-table-body');

// Drawer Elements
const deviceDrawer = document.getElementById('device-drawer');
const btnCloseDrawer = document.getElementById('btn-close-drawer');
const drawerName = document.getElementById('drawer-name');
const drawerCategory = document.getElementById('drawer-category');
const drawerIcon = document.getElementById('drawer-icon');
const drawerIconBox = document.getElementById('drawer-icon-box');
const drawerIp = document.getElementById('drawer-ip');
const drawerMac = document.getElementById('drawer-mac');
const drawerVendor = document.getElementById('drawer-vendor');
const drawerOs = document.getElementById('drawer-os');
const drawerOsIcon = document.getElementById('drawer-os-icon');
const drawerNetbios = document.getElementById('drawer-netbios');
const drawerWorkgroup = document.getElementById('drawer-workgroup');
const drawerTitleRow = document.getElementById('drawer-title-row');
const drawerHttpTitle = document.getElementById('drawer-http-title');
const drawerPortsList = document.getElementById('drawer-ports-list');
const drawerBtnHttp = document.getElementById('drawer-btn-http');
const drawerBtnHttps = document.getElementById('drawer-btn-https');

// Diagnostic Buttons inside Drawer
const btnLivePing = document.getElementById('btn-live-ping');
const pingResultBox = document.getElementById('ping-result-box');
const pingRttVal = document.getElementById('ping-rtt-val');
const btnWol = document.getElementById('btn-wol');
const wolResultBox = document.getElementById('wol-result-box');
const btnDeepPortScan = document.getElementById('btn-deep-port-scan');

// Customization Inputs
const inputCustomName = document.getElementById('input-custom-name');
const inputCustomNotes = document.getElementById('input-custom-notes');
const btnSaveCustom = document.getElementById('btn-save-custom');

// Export & Config
const btnExportDropdown = document.getElementById('btn-export-dropdown');
const exportMenu = document.getElementById('export-menu');
const btnConfig = document.getElementById('btn-config');
const configModal = document.getElementById('config-modal');
const btnCloseModal = document.getElementById('btn-close-modal');
const btnSaveModal = document.getElementById('btn-save-modal');
const inputCidr = document.getElementById('input-cidr');
const inputGateway = document.getElementById('input-gateway');
const inputPorts = document.getElementById('input-ports');
const inputMonitorInterval = document.getElementById('input-monitor-interval');

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
    initTabs();
    initExportDropdown();
    initConfigModal();
    initVisGraph();
    initLayoutControls();
    initDrawer();
    initSearch();
    initSurveillanceControls();
    initAlertsModal();
    await fetchNetworkInfo();
    await checkScanStatus();
    connectWebSocket();
});

// --- Tab Switching ---
function initTabs() {
    tabMapBtn.addEventListener('click', () => {
        tabMapBtn.classList.add('active');
        tabTableBtn.classList.remove('active');
        viewMap.classList.remove('hidden');
        viewTable.classList.add('hidden');
        document.getElementById('layout-controls').classList.remove('hidden');
        document.getElementById('map-controls').classList.remove('hidden');
        if (networkGraph) networkGraph.redraw();
    });

    tabTableBtn.addEventListener('click', () => {
        tabTableBtn.classList.add('active');
        tabMapBtn.classList.remove('active');
        viewTable.classList.remove('hidden');
        viewMap.classList.add('hidden');
        document.getElementById('layout-controls').classList.add('hidden');
        document.getElementById('map-controls').classList.add('hidden');
    });
}

function initExportDropdown() {
    btnExportDropdown.addEventListener('click', (e) => {
        e.stopPropagation();
        exportMenu.classList.toggle('hidden');
    });
    document.addEventListener('click', () => exportMenu.classList.add('hidden'));
}

function initConfigModal() {
    btnConfig.addEventListener('click', () => configModal.classList.remove('hidden'));
    btnCloseModal.addEventListener('click', () => configModal.classList.add('hidden'));
    btnSaveModal.addEventListener('click', () => configModal.classList.add('hidden'));
}

// --- Fetch Network Interfaces ---
async function fetchNetworkInfo() {
    try {
        const resp = await fetch('/api/network/interfaces');
        const data = await resp.json();
        if (data.default) {
            defaultNetwork = data.default;
            navSubnet.textContent = defaultNetwork.network_cidr || '--';
            navGateway.textContent = defaultNetwork.gateway || '--';
            navLocalIp.textContent = defaultNetwork.ip || '--';

            inputCidr.placeholder = defaultNetwork.network_cidr;
            inputGateway.placeholder = defaultNetwork.gateway;
        }
    } catch (e) {
        console.error('Error fetching network info:', e);
    }
}

// --- Check scan status ---
async function checkScanStatus() {
    try {
        const resp = await fetch('/api/scan/status');
        const data = await resp.json();
        if (data.is_monitoring) {
            updateMonitoringUI(true);
        }
        if (data.results && data.results.devices && data.results.devices.length > 0) {
            renderResults(data.results);
        } else {
            graphPlaceholder.classList.remove('hidden');
        }
    } catch (e) {
        console.error('Error fetching scan status:', e);
    }
}

// --- Vis.js Topology Graph Setup ---
function initVisGraph() {
    const options = getVisOptions('physics');
    networkGraph = new vis.Network(graphContainer, networkData, options);

    networkGraph.on('click', (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = networkData.nodes.get(nodeId);
            if (node && node.device_info) {
                openDeviceDrawer(node.device_info);
            }
        }
    });

    btnFitMap.addEventListener('click', () => {
        networkGraph.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
    });
}

function getVisOptions(layoutType) {
    if (layoutType === 'tree') {
        return {
            layout: {
                hierarchical: {
                    enabled: true,
                    direction: 'UD',
                    sortMethod: 'directed',
                    levelSeparation: 120,
                    nodeSpacing: 110,
                    treeSpacing: 150
                }
            },
            physics: false
        };
    } else if (layoutType === 'radial') {
        return {
            layout: { hierarchical: { enabled: false } },
            physics: {
                enabled: true,
                solver: 'repulsion',
                repulsion: {
                    nodeDistance: 130,
                    centralGravity: 0.25,
                    springLength: 140,
                    springConstant: 0.05
                },
                stabilization: { iterations: 120 }
            }
        };
    } else {
        // Force-Directed Physics
        return {
            layout: { hierarchical: { enabled: false } },
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -70,
                    centralGravity: 0.015,
                    springLength: 120,
                    springConstant: 0.08,
                    damping: 0.6
                },
                stabilization: { iterations: 150 }
            }
        };
    }
}

function initLayoutControls() {
    btnLayoutPhysics.addEventListener('click', () => switchLayout('physics'));
    btnLayoutTree.addEventListener('click', () => switchLayout('tree'));
    btnLayoutRadial.addEventListener('click', () => switchLayout('radial'));
}

function switchLayout(type) {
    currentLayout = type;
    [btnLayoutPhysics, btnLayoutTree, btnLayoutRadial].forEach(btn => {
        btn.classList.remove('bg-slate-800', 'text-cyan-400', 'font-medium');
        btn.classList.add('text-slate-400');
    });

    if (type === 'physics') {
        btnLayoutPhysics.classList.add('bg-slate-800', 'text-cyan-400', 'font-medium');
        btnLayoutPhysics.classList.remove('text-slate-400');
    } else if (type === 'tree') {
        btnLayoutTree.classList.add('bg-slate-800', 'text-cyan-400', 'font-medium');
        btnLayoutTree.classList.remove('text-slate-400');
    } else if (type === 'radial') {
        btnLayoutRadial.classList.add('bg-slate-800', 'text-cyan-400', 'font-medium');
        btnLayoutRadial.classList.remove('text-slate-400');
    }

    if (networkGraph) {
        networkGraph.setOptions(getVisOptions(type));
        setTimeout(() => networkGraph.fit({ animation: { duration: 600 } }), 300);
    }
}

// --- WebSocket Stream ---
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/scan`;

    socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWsMessage(msg);
        } catch (e) {
            console.error('WS parse error:', e);
        }
    };

    socket.onclose = () => setTimeout(connectWebSocket, 3000);
}

function handleWsMessage(msg) {
    if (msg.step === 'status') {
        if (msg.is_scanning) setScanningState(true);
        if (msg.is_monitoring) updateMonitoringUI(true);
        if (msg.last_results && msg.last_results.devices && msg.last_results.devices.length > 0) {
            renderResults(msg.last_results);
        }
    } else if (['arp_scan', 'enrichment', 'topology'].includes(msg.step)) {
        setScanningState(true);
        updateProgress(msg.progress || 0, msg.message || 'Scan en cours...');
    } else if (msg.step === 'done') {
        setScanningState(false);
        updateProgress(100, msg.message || 'Scan terminé !');
        setTimeout(() => scanBanner.classList.add('hidden'), 5000);
        if (msg.results) renderResults(msg.results);
    } else if (msg.step === 'alert') {
        handleNewAlert(msg.alert);
    }
}

function setScanningState(scanning) {
    if (scanning) {
        scanBanner.classList.remove('hidden');
        btnStartScan.disabled = true;
        btnStartScan.classList.add('opacity-70', 'cursor-not-allowed');
        scanBtnText.textContent = 'Scan en cours...';
        scanIcon.className = 'fa-solid fa-circle-notch fa-spin';
    } else {
        btnStartScan.disabled = false;
        btnStartScan.classList.remove('opacity-70', 'cursor-not-allowed');
        scanBtnText.textContent = 'Lancer le Scan';
        scanIcon.className = 'fa-solid fa-bolt';
    }
}

function updateProgress(percent, msg) {
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;
    bannerMessage.textContent = msg;
}

// --- Start Scan Trigger ---
btnStartScan.addEventListener('click', async () => {
    const payload = {
        network_cidr: inputCidr.value.trim() || null,
        gateway_ip: inputGateway.value.trim() || null,
        do_port_scan: inputPorts.checked
    };

    try {
        setScanningState(true);
        updateProgress(5, "Lancement du processus de découverte...");
        await fetch('/api/scan/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error('Error starting scan:', e);
        setScanningState(false);
    }
});

// --- Surveillance Controls & Alerts ---
function initSurveillanceControls() {
    btnToggleMonitor.addEventListener('click', async () => {
        const nextState = !isMonitoring;
        const interval = parseInt(inputMonitorInterval.value) || 45;
        try {
            const resp = await fetch('/api/monitor/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: nextState, interval: interval })
            });
            const data = await resp.json();
            updateMonitoringUI(data.status === 'started');
        } catch (e) {
            console.error('Toggle monitor error:', e);
        }
    });
}

function updateMonitoringUI(active) {
    isMonitoring = active;
    if (active) {
        monitorDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-ping';
        monitorStatusText.textContent = 'Actif';
        monitorStatusText.className = 'font-semibold text-emerald-400';
    } else {
        monitorDot.className = 'w-2 h-2 rounded-full bg-slate-500';
        monitorStatusText.textContent = 'Off';
        monitorStatusText.className = 'font-semibold text-slate-400';
    }
}

function initAlertsModal() {
    btnAlerts.addEventListener('click', async () => {
        alertsModal.classList.remove('hidden');
        await loadAlerts();
    });
    btnCloseAlerts.addEventListener('click', () => alertsModal.classList.add('hidden'));
    btnDismissAlerts.addEventListener('click', () => alertsModal.classList.add('hidden'));
    btnClearAlerts.addEventListener('click', async () => {
        await fetch('/api/monitor/alerts', { method: 'DELETE' });
        alertCount = 0;
        alertsBadge.classList.add('hidden');
        alertsContainer.innerHTML = `
            <div class="p-6 text-center text-slate-500">
                <i class="fa-solid fa-shield-cat text-3xl mb-2 text-slate-600"></i>
                <p>Toutes les alertes ont été effacées.</p>
            </div>
        `;
    });
}

async function loadAlerts() {
    try {
        const resp = await fetch('/api/monitor/alerts');
        const data = await resp.json();
        renderAlertsList(data.alerts || []);
    } catch (e) {
        console.error('Error loading alerts:', e);
    }
}

function handleNewAlert(alert) {
    alertCount++;
    alertsBadge.textContent = alertCount;
    alertsBadge.classList.remove('hidden');
    playAlertSound();
    // Prepend to alerts container if open
    loadAlerts();
}

function renderAlertsList(alerts) {
    if (!alerts || alerts.length === 0) {
        alertsContainer.innerHTML = `
            <div class="p-6 text-center text-slate-500">
                <i class="fa-solid fa-shield-cat text-3xl mb-2 text-slate-600"></i>
                <p>Aucune alerte pour l'instant.</p>
            </div>
        `;
        return;
    }

    alertsContainer.innerHTML = alerts.slice().reverse().map(al => `
        <div class="p-3 rounded-xl bg-slate-900 border border-rose-900/40 flex items-start gap-3">
            <span class="w-8 h-8 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center shrink-0 mt-0.5">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </span>
            <div class="flex-1">
                <div class="flex items-center justify-between">
                    <span class="font-bold text-white text-xs">${al.title || 'Nouvel équipement'}</span>
                    <span class="font-mono text-[10px] text-slate-500">${al.timestamp}</span>
                </div>
                <p class="text-slate-300 text-[11px] mt-0.5">${al.message}</p>
                <div class="mt-1 flex items-center gap-3 text-[10px] font-mono text-cyan-400">
                    <span>IP: ${al.device?.ip}</span>
                    <span>MAC: ${al.device?.mac}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function playAlertSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
        osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.15); // A5
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) {}
}

// --- Render Results (Graph & Table) ---
function renderResults(results) {
    allDevices = results.devices || [];
    graphPlaceholder.classList.add('hidden');

    statTotal.textContent = allDevices.length;
    statPcs.textContent = allDevices.filter(d => ['computer', 'server'].includes(d.category)).length;
    statMobiles.textContent = allDevices.filter(d => d.category === 'mobile').length;
    statIot.textContent = allDevices.filter(d => ['iot', 'printer', 'tv', 'console'].includes(d.category)).length;
    tabCountBadge.textContent = allDevices.length;

    if (results.topology && results.topology.nodes) {
        networkData.nodes.clear();
        networkData.edges.clear();
        networkData.nodes.add(results.topology.nodes);
        networkData.edges.add(results.topology.edges);
        networkGraph.setOptions(getVisOptions(currentLayout));
        setTimeout(() => networkGraph.fit({ animation: { duration: 600 } }), 200);
    }

    renderTable(allDevices);
}

// --- Render Table ---
function renderTable(devices) {
    if (!devices || devices.length === 0) {
        deviceTableBody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-12 text-slate-500 font-sans">
                    Aucun appareil correspondant aux critères de recherche.
                </td>
            </tr>
        `;
        return;
    }

    deviceTableBody.innerHTML = devices.map(dev => {
        const isGw = dev.is_gateway;
        const iconClass = getCategoryIcon(dev.category);
        const badgeClass = `badge-${dev.category || 'unknown'}`;
        const displayName = dev.display_name || dev.hostname || dev.ip;
        const osName = dev.os_info?.os_name || 'Inconnu';
        
        const portsPills = (dev.open_ports && dev.open_ports.length > 0)
            ? dev.open_ports.slice(0, 3).map(p => 
                `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-cyan-300 border border-slate-700 font-mono">${p.port}/${p.service}</span>`
              ).join(' ') + (dev.open_ports.length > 3 ? `<span class="text-[10px] text-slate-500">+${dev.open_ports.length - 3}</span>` : '')
            : '<span class="text-slate-600 text-[11px]">-</span>';

        return `
            <tr class="device-row cursor-pointer" onclick='openDeviceDrawer(${JSON.stringify(dev)})'>
                <td class="py-3 px-4 flex items-center gap-2.5 font-sans font-medium text-slate-200">
                    <span class="w-7 h-7 rounded-lg flex items-center justify-center text-xs" style="background-color: ${dev.color}22; color: ${dev.color}">
                        <i class="${iconClass}"></i>
                    </span>
                    <span class="truncate max-w-[150px]">${displayName}</span>
                    ${isGw ? '<span class="text-[10px] px-1.5 py-0.2 rounded bg-blue-950 border border-blue-800 text-blue-400">Passerelle</span>' : ''}
                </td>
                <td class="py-3 px-4 font-mono font-bold text-cyan-300">${dev.ip}</td>
                <td class="py-3 px-4 font-mono text-slate-400">${dev.mac}</td>
                <td class="py-3 px-4 font-sans text-slate-300 max-w-[140px] truncate">${dev.vendor || 'Inconnu'}</td>
                <td class="py-3 px-4 font-sans text-slate-300 text-xs truncate max-w-[120px]">${osName}</td>
                <td class="py-3 px-4 font-sans">
                    <span class="px-2 py-0.5 rounded-full text-[11px] font-medium ${badgeClass}">
                        ${dev.category_label || dev.category}
                    </span>
                </td>
                <td class="py-3 px-4 font-sans">${portsPills}</td>
                <td class="py-3 px-4 text-right font-mono text-emerald-400 font-medium">${dev.latency_ms || 1} ms</td>
                <td class="py-3 px-4 text-center">
                    <button class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition" title="Inspecter l'appareil">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function getCategoryIcon(cat) {
    const map = {
        router: 'fa-solid fa-server',
        server: 'fa-solid fa-server',
        computer: 'fa-solid fa-desktop',
        mobile: 'fa-solid fa-mobile-screen',
        printer: 'fa-solid fa-print',
        iot: 'fa-solid fa-microchip',
        tv: 'fa-solid fa-tv',
        console: 'fa-solid fa-gamepad',
        unknown: 'fa-solid fa-network-wired'
    };
    return map[cat] || 'fa-solid fa-network-wired';
}

function initSearch() {
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const filtered = allDevices.filter(d => 
            (d.ip && d.ip.toLowerCase().includes(query)) ||
            (d.mac && d.mac.toLowerCase().includes(query)) ||
            (d.display_name && d.display_name.toLowerCase().includes(query)) ||
            (d.hostname && d.hostname.toLowerCase().includes(query)) ||
            (d.vendor && d.vendor.toLowerCase().includes(query))
        );
        renderTable(filtered);
    });
}

// --- Device Details Drawer & Diagnostics ---
function initDrawer() {
    btnCloseDrawer.addEventListener('click', closeDeviceDrawer);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDeviceDrawer();
    });

    // Live Ping Click
    btnLivePing.addEventListener('click', async () => {
        if (!currentSelectedDevice) return;
        pingResultBox.classList.remove('hidden');
        pingRttVal.textContent = 'Mesure en cours...';
        try {
            const resp = await fetch(`/api/device/${currentSelectedDevice.ip}/ping`);
            const data = await resp.json();
            if (data.alive) {
                pingRttVal.textContent = `${data.rtt_ms} ms (En ligne)`;
                pingRttVal.className = 'font-mono font-bold text-emerald-400';
            } else {
                pingRttVal.textContent = 'Inaccessible / Timeout';
                pingRttVal.className = 'font-mono font-bold text-rose-400';
            }
        } catch (e) {
            pingRttVal.textContent = 'Erreur test';
        }
    });

    // Wake-on-LAN Click
    btnWol.addEventListener('click', async () => {
        if (!currentSelectedDevice || !currentSelectedDevice.mac) return;
        wolResultBox.classList.remove('hidden');
        wolResultBox.textContent = 'Envoi du paquet magique Wake-on-LAN...';
        try {
            const resp = await fetch(`/api/device/${encodeURIComponent(currentSelectedDevice.mac)}/wol`, { method: 'POST' });
            const data = await resp.json();
            wolResultBox.textContent = data.message || 'Paquet envoyé !';
            setTimeout(() => wolResultBox.classList.add('hidden'), 5000);
        } catch (e) {
            wolResultBox.textContent = 'Erreur envoi WOL';
        }
    });

    // Deep Port Scan
    btnDeepPortScan.addEventListener('click', async () => {
        if (!currentSelectedDevice) return;
        drawerPortsList.innerHTML = `<span class="text-xs text-cyan-400 italic"><i class="fa-solid fa-spinner fa-spin"></i> Scan étendu des ports 1 à 1024 en cours...</span>`;
        try {
            const resp = await fetch(`/api/device/${currentSelectedDevice.ip}/scan-ports?start=1&end=1024`);
            const data = await resp.json();
            renderDrawerPorts(data.open_ports);
        } catch (e) {
            drawerPortsList.innerHTML = `<span class="text-xs text-rose-400">Erreur lors du scan approfondi.</span>`;
        }
    });

    // Save Customization
    btnSaveCustom.addEventListener('click', async () => {
        if (!currentSelectedDevice || !currentSelectedDevice.mac) return;
        const nameVal = inputCustomName.value.trim();
        const notesVal = inputCustomNotes.value.trim();
        try {
            await fetch(`/api/device/${encodeURIComponent(currentSelectedDevice.mac)}/customize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ custom_name: nameVal, notes: notesVal })
            });
            currentSelectedDevice.custom_name = nameVal;
            currentSelectedDevice.display_name = nameVal || currentSelectedDevice.hostname;
            currentSelectedDevice.notes = notesVal;
            drawerName.textContent = currentSelectedDevice.display_name;
            renderTable(allDevices);
            // Refresh node label in graph
            const nodeId = `node_${currentSelectedDevice.ip.replace(/\./g, '_')}`;
            const existingNode = networkData.nodes.get(nodeId);
            if (existingNode) {
                networkData.nodes.update({ id: nodeId, label: `${currentSelectedDevice.display_name}\n${currentSelectedDevice.ip}` });
            }
            alert('Personnalisation enregistrée avec succès !');
        } catch (e) {
            alert('Erreur lors de l\'enregistrement de la personnalisation');
        }
    });
}

function openDeviceDrawer(device) {
    if (!device) return;
    currentSelectedDevice = device;

    drawerName.textContent = device.display_name || device.hostname || device.ip;
    drawerCategory.textContent = device.category_label || 'Périphérique Réseau';

    drawerIcon.className = getCategoryIcon(device.category);
    drawerIconBox.style.color = device.color || '#38bdf8';
    drawerIconBox.style.backgroundColor = `${device.color || '#38bdf8'}22`;

    drawerIp.textContent = device.ip || '--';
    drawerMac.textContent = device.mac || '--';
    drawerVendor.textContent = device.vendor || 'Inconnu';
    
    // OS Fingerprint
    const osInfo = device.os_info || { os_name: 'Non déterminé', os_icon: 'fa-solid fa-question' };
    drawerOs.textContent = osInfo.os_name;
    drawerOsIcon.className = osInfo.os_icon;

    drawerNetbios.textContent = device.netbios_name || 'Non disponible';
    drawerWorkgroup.textContent = device.workgroup || 'Non disponible';

    // HTTP banner title
    if (device.http_banners && device.http_banners.length > 0 && device.http_banners[0].title) {
        drawerTitleRow.classList.remove('hidden');
        drawerHttpTitle.textContent = device.http_banners[0].title;
    } else {
        drawerTitleRow.classList.add('hidden');
    }

    // Customization inputs
    inputCustomName.value = device.custom_name || '';
    inputCustomNotes.value = device.notes || '';

    // Reset diagnostic boxes
    pingResultBox.classList.add('hidden');
    wolResultBox.classList.add('hidden');

    // Render ports
    renderDrawerPorts(device.open_ports || []);

    // Action buttons
    drawerBtnHttp.href = `http://${device.ip}`;
    drawerBtnHttps.href = `https://${device.ip}`;

    deviceDrawer.classList.remove('translate-x-full');
}

function renderDrawerPorts(ports) {
    if (ports && ports.length > 0) {
        drawerPortsList.innerHTML = ports.map(p => `
            <div class="flex items-center justify-between p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span class="font-mono font-bold text-cyan-300">Port ${p.port}</span>
                </div>
                <span class="text-slate-300 font-sans">${p.service}</span>
            </div>
        `).join('');
    } else {
        drawerPortsList.innerHTML = `<span class="text-xs text-slate-500 italic">Aucun port ouvert détecté sur cet appareil.</span>`;
    }
}

function closeDeviceDrawer() {
    deviceDrawer.classList.add('translate-x-full');
    currentSelectedDevice = null;
}

window.copyToClipboard = function(elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => alert(`Copié dans le presse-papiers : ${text}`));
};
