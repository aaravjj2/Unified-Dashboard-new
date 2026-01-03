
if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.tv = {
    render_chart: function (data, trigger) {
        if (!data) {
            return window.dash_clientside.no_update;
        }

        const containerId = 'scanner-tv-chart-container';
        const container = document.getElementById(containerId);

        if (!container) {
            console.warn("TV Chart container not found:", containerId);
            return window.dash_clientside.no_update;
        }

        console.log("📈 Rendering TV Chart manually with", data.length, "points");

        // Ensure LightweightCharts is loaded
        if (typeof LightweightCharts === 'undefined') {
            console.error("LightweightCharts library not loaded!");
            container.innerHTML = "<div style='color:red; padding:10px'>Error: Chart library not loaded</div>";
            return window.dash_clientside.no_update;
        }

        // Clean up existing chart if it exists
        if (container._chart) {
            // Check if data is same? No, always redraw for now to be safe
            container._chart.remove();
            container._chart = null;
            container.innerHTML = ''; // Clear any internal divs
        } else {
            container.innerHTML = ''; // Clear on first load
        }

        // Create Chart
        const chart = LightweightCharts.createChart(container, {
            layout: {
                background: { type: 'solid', color: '#0f172a' }, // ALPACA_DARK['paper'] approx
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: '#1e293b' },
                horzLines: { color: '#1e293b' },
            },
            width: container.clientWidth || 900,
            height: 450,
            autoSize: true, // Use built-in autosize if strictly supported, else manual
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: '#1e293b',
            },
            rightPriceScale: {
                borderColor: '#1e293b',
            },
        });

        // LightweightCharts v5 API: Use addSeries with series type
        const candlestickSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
            upColor: '#22c55e',          // Success green
            downColor: '#ef4444',        // Danger red
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        candlestickSeries.setData(data);

        // Auto-fit content
        chart.timeScale().fitContent();

        // Save instance
        container._chart = chart;

        // Resize handler
        const resizeObserver = new ResizeObserver(entries => {
            if (entries.length === 0 || !entries[0].contentRect) return;
            const newRect = entries[0].contentRect;
            chart.applyOptions({ width: newRect.width, height: newRect.height });
        });

        resizeObserver.observe(container);
        container._resizeObserver = resizeObserver; // Store for cleanup if needed

        return "Chart Rendered " + new Date().toISOString();
    }
};
