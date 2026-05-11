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

    // Initialize WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${API_BASE_URL}/ws/market`);

    socket.onopen = () => {
        wsStatus.innerText = 'Connected';
        wsStatus.style.color = '#00ff9d';
    };

    socket.onclose = () => {
        wsStatus.innerText = 'Disconnected';
        wsStatus.style.color = '#ff3e3e';
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
        if (data.SENSEX) {
            sensexPrice.innerText = data.SENSEX.price.toLocaleString();
            sensexChange.innerText = `${data.SENSEX.change > 0 ? '+' : ''}${data.SENSEX.change} (${data.SENSEX.percent_change}%)`;
            sensexChange.className = `change ${data.SENSEX.change >= 0 ? 'pos' : 'neg'}`;
        }
        if (data.NIFTY) {
            niftyPrice.innerText = data.NIFTY.price.toLocaleString();
            niftyChange.innerText = `${data.NIFTY.change > 0 ? '+' : ''}${data.NIFTY.change} (${data.NIFTY.percent_change}%)`;
            niftyChange.className = `change ${data.NIFTY.change >= 0 ? 'pos' : 'neg'}`;
        }
    }

    function addSignalToTable(signal, isNew = false) {
        const row = document.createElement('tr');
        if (isNew) row.className = 'live-signal-alert';
        
        row.innerHTML = `
            <td style="font-weight: 600;">${signal.symbol}</td>
            <td><span class="badge ${signal.type === 'BUY' ? 'badge-buy' : 'badge-sell'}">${signal.type}</span></td>
            <td>${signal.entry_price}</td>
            <td>${signal.target_1}</td>
            <td>${signal.stop_loss}</td>
            <td>${signal.confidence}%</td>
        `;

        if (signalsBody.firstChild) {
            signalsBody.insertBefore(row, signalsBody.firstChild);
        } else {
            signalsBody.appendChild(row);
        }

        // Limit to 10 signals
        if (signalsBody.children.length > 10) {
            signalsBody.removeChild(signalsBody.lastChild);
        }
    }

    // Fetch initial signals
    const httpProtocol = window.location.protocol;
    fetch(`${httpProtocol}//${API_BASE_URL}/api/signals`)
        .then(res => res.json())
        .then(data => {
            data.forEach(signal => addSignalToTable(signal));
        });
});
