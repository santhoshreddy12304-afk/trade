// AI Trader Pro - Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
    // Determine backend URL (Use current host or set a custom one here)
    const API_BASE_URL = window.location.host; 
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    const wsStatus = document.getElementById('ws-status');
    const sensexPrice = document.getElementById('sensex-price');
    const sensexChange = document.getElementById('sensex-change');
    const niftyPrice = document.getElementById('nifty-price');
    const niftyChange = document.getElementById('nifty-change');
    const signalsBody = document.getElementById('signals-body');
    const brokerName = document.getElementById('broker-name');
    const tradingMode = document.getElementById('trading-mode');
    const httpProtocol = window.location.protocol;

    // --- BROKER & WS INIT ---
    fetch(`${window.location.protocol}//${API_BASE_URL}/api/broker/status`)
        .then(res => res.json())
        .then(data => {
            if (brokerName) brokerName.innerText = data.broker;
            if (tradingMode) {
                tradingMode.innerText = data.mode.toUpperCase();
                tradingMode.style.color = data.mode === 'live' ? '#ff3e3e' : '#00ff9d';
            }
        });

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${API_BASE_URL}/ws/market`);

    socket.onopen = () => {
        if (wsStatus) {
            wsStatus.innerText = 'Connected';
            wsStatus.style.color = '#00ff9d';
        }
    };

    socket.onclose = () => {
        if (wsStatus) {
            wsStatus.innerText = 'Disconnected';
            wsStatus.style.color = '#ff3e3e';
        }
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'MARKET_UPDATE') {
            updateMarketData(message.data);
        } else if (message.type === 'SIGNAL') {
            addSignalToTable(message.data, true);
        }
    };

    function updateMarketData(data) {
        if (data.SENSEX && sensexPrice) {
            sensexPrice.innerText = data.SENSEX.price.toLocaleString();
            sensexChange.innerText = `${data.SENSEX.change > 0 ? '+' : ''}${data.SENSEX.change} (${data.SENSEX.percent_change}%)`;
            sensexChange.className = `change ${data.SENSEX.change >= 0 ? 'pos' : 'neg'}`;
        }
        if (data.NIFTY && niftyPrice) {
            niftyPrice.innerText = data.NIFTY.price.toLocaleString();
            niftyChange.innerText = `${data.NIFTY.change > 0 ? '+' : ''}${data.NIFTY.change} (${data.NIFTY.percent_change}%)`;
            niftyChange.className = `change ${data.NIFTY.change >= 0 ? 'pos' : 'neg'}`;
        }
    }

    function addSignalToTable(signal, isNew = false) {
        if (!signalsBody) return;
        const row = document.createElement('tr');
        if (isNew) row.className = 'live-signal-alert';
        
        row.innerHTML = `
            <td style="font-weight: 600;">${signal.symbol}</td>
            <td><span class="badge ${signal.type.includes('CALL') ? 'badge-buy' : 'badge-sell'}">${signal.type}</span></td>
            <td>${signal.entry_min || signal.entry_price}</td>
            <td>${signal.target_1}</td>
            <td>${signal.stop_loss}</td>
            <td>${signal.confidence}%</td>
        `;

        if (signalsBody.firstChild) {
            signalsBody.insertBefore(row, signalsBody.firstChild);
        } else {
            signalsBody.appendChild(row);
        }
        if (signalsBody.children.length > 10) signalsBody.removeChild(signalsBody.lastChild);
    }

    // Fetch initial signals
    fetch(`${window.location.protocol}//${API_BASE_URL}/api/signals`)
        .then(res => res.json())
        .then(data => {
            data.forEach(signal => addSignalToTable(signal));
        });

    // --- VIEW MANAGEMENT ---
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.view-section');

    function switchView(viewId) {
        sections.forEach(s => s.classList.remove('active'));
        const targetSection = document.getElementById(viewId);
        if (targetSection) {
            targetSection.classList.add('active');
        }

        // Trigger data fetch based on view
        if (viewId === 'option-chain-view') {
            loadOptionChain();
        } else if (viewId === 'history-view') {
            loadTradeHistory();
        } else if (viewId === 'dashboard-view') {
            updatePortfolio();
        }
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            const viewId = item.getAttribute('data-view');
            if (viewId) switchView(viewId);
        });
    });

    // --- OPTION CHAIN LOGIC ---
    const ocIndexSelect = document.getElementById('oc-index-select');
    const ocBody = document.getElementById('oc-body');

    if (ocIndexSelect) {
        ocIndexSelect.addEventListener('change', () => loadOptionChain());
    }

    async function loadOptionChain() {
        const index = ocIndexSelect.value;
        ocBody.innerHTML = '<tr><td colspan="7" style="padding: 3rem;">Loading live option chain...</td></tr>';
        
        try {
            const res = await fetch(`${window.location.protocol}//${API_BASE_URL}/api/option-chain/${index}`);
            const data = await res.json();
            
            if (data.error) {
                ocBody.innerHTML = `<tr><td colspan="7" style="color: var(--accent-secondary); padding: 3rem;">${data.error}</td></tr>`;
                return;
            }

            ocBody.innerHTML = '';
            // Render only top 20 strikes near spot for clarity
            const spot = data.underlyingValue || 0;
            const records = data.data.filter(r => Math.abs(r.strikePrice - spot) < (index === 'NIFTY 50' ? 500 : 1500));
            
            records.forEach(row => {
                const tr = document.createElement('tr');
                if (Math.abs(row.strikePrice - spot) < 25) tr.className = 'atm-row';
                
                tr.innerHTML = `
                    <td style="color: var(--text-muted)">${row.CE?.openInterest || 0}</td>
                    <td>${row.CE?.totalTradedVolume || 0}</td>
                    <td style="color: var(--accent-primary); font-weight: 600;">${row.CE?.lastPrice || '-'}</td>
                    <td class="strike-header">${row.strikePrice}</td>
                    <td style="color: var(--accent-secondary); font-weight: 600;">${row.PE?.lastPrice || '-'}</td>
                    <td>${row.PE?.totalTradedVolume || 0}</td>
                    <td style="color: var(--text-muted)">${row.PE?.openInterest || 0}</td>
                `;
                ocBody.appendChild(tr);
            });
        } catch (err) {
            ocBody.innerHTML = '<tr><td colspan="7">Failed to load option chain.</td></tr>';
        }
    }

    // --- HISTORY LOGIC ---
    const historyBody = document.getElementById('history-body');

    async function loadTradeHistory() {
        try {
            const res = await fetch(`${window.location.protocol}//${API_BASE_URL}/api/trades/history`);
            const trades = await res.json();
            
            historyBody.innerHTML = '';
            trades.forEach(trade => {
                const tr = document.createElement('tr');
                const date = new Date(trade.timestamp).toLocaleString();
                const pnlClass = trade.pnl > 0 ? 'pos' : (trade.pnl < 0 ? 'neg' : '');
                
                tr.innerHTML = `
                    <td style="font-size: 0.75rem; color: var(--text-muted)">${date}</td>
                    <td style="font-weight: 600;">${trade.symbol}</td>
                    <td><span class="badge ${trade.type === 'BUY' ? 'badge-buy' : 'badge-sell'}">${trade.type}</span></td>
                    <td>${trade.entry_price}</td>
                    <td>${trade.exit_price || '-'}</td>
                    <td class="change ${pnlClass}">₹ ${trade.pnl.toFixed(2)}</td>
                    <td><span class="status-badge" style="border-color: rgba(255,255,255,0.1); color: var(--text-muted)">${trade.status}</span></td>
                `;
                historyBody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error loading history:", err);
        }
    }

    // --- PORTFOLIO LOGIC ---
    const pnlTotal = document.getElementById('pnl-total');
    const pnlChange = document.getElementById('pnl-change');

    async function updatePortfolio() {
        try {
            const res = await fetch(`${window.location.protocol}//${API_BASE_URL}/api/portfolio`);
            const data = await res.json();
            
            if (pnlTotal) pnlTotal.innerText = `₹ ${data.paper.total_pnl.toLocaleString()}`;
            if (pnlChange) {
                pnlChange.innerText = `${data.paper.total_pnl >= 0 ? '+' : ''}₹ ${data.paper.total_pnl} (Today)`;
                pnlChange.className = data.paper.total_pnl >= 0 ? 'pos' : 'neg';
            }
        } catch (err) {
            console.error("Error updating portfolio:", err);
        }
    }

    // Initial Dashboard Load
    updatePortfolio();

    // Handle Force Signal Button
    const forceSignalBtn = document.getElementById('force-signal-btn');
    if (forceSignalBtn) {
        forceSignalBtn.addEventListener('click', async () => {
            forceSignalBtn.disabled = true;
            const originalContent = forceSignalBtn.innerHTML;
            forceSignalBtn.innerHTML = '<i data-lucide="loader" class="spin"></i> SCANNING...';
            lucide.createIcons();
            
            try {
                await fetch(`${httpProtocol}//${API_BASE_URL}/api/force-signal`, { method: 'POST' });
            } catch (err) {
                console.error("Error forcing signal:", err);
            } finally {
                setTimeout(() => {
                    forceSignalBtn.disabled = false;
                    forceSignalBtn.innerHTML = originalContent;
                    lucide.createIcons();
                }, 1500);
            }
        });
    }
});
