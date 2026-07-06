// System metrics handling

class MetricsWidget {
    constructor(refreshInterval = 1000) {
        this.refreshInterval = refreshInterval;
        this.metricsEndpoint = '/api/metrics';
        this.intervalId = null;
    }

    /**
     * Initialize the metrics widget
     */
    init() {
        this.updateMetrics();
        this.intervalId = setInterval(() => this.updateMetrics(), this.refreshInterval);
    }

    /**
     * Stop periodic updates
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    /**
     * Fetch current metrics from the server
     */
    async updateMetrics() {
        try {
            const response = await fetch(this.metricsEndpoint);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const data = await response.json();
            this.updateUI(data);
        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    }

    /**
     * Update UI with current metrics
     */
    updateUI(data) {
        this.updateTile('cpu', data.cpu.usage, this.hottestSensor(data.cpu.temperature));
        this.updateTile('memory', data.memory.percent,
            `${this.formatBytes(data.memory.used)} / ${this.formatBytes(data.memory.total)}`);
        this.updateTile('disk', data.disk.percent,
            `${this.formatBytes(data.disk.used)} / ${this.formatBytes(data.disk.total)}`);

        const gpuTile = document.getElementById('gpu-tile');
        if (data.gpu.available && data.gpu.gpus.length > 0) {
            gpuTile.style.display = '';
            const gpu = data.gpu.gpus[0];
            this.updateTile('gpu', gpu.util_percent, `${gpu.temperature.toFixed(0)}°C`);
        } else {
            gpuTile.style.display = 'none';
        }
    }

    /**
     * Format the hottest CPU sensor reading, or an empty string if unavailable
     */
    hottestSensor(temperature) {
        if (!temperature.available || temperature.sensors.length === 0) {
            return '';
        }
        const hottest = temperature.sensors.reduce((a, b) => (b.temp > a.temp ? b : a));
        return `${hottest.temp.toFixed(0)}°C`;
    }

    /**
     * Update a metric tile's value, bar width/color, and sub-detail text
     */
    updateTile(prefix, percent, sub) {
        const value = document.getElementById(`${prefix}-value`);
        const bar = document.getElementById(`${prefix}-bar`);
        const subEl = document.getElementById(`${prefix}-sub`);

        value.textContent = `${percent.toFixed(0)}%`;
        bar.style.width = `${percent}%`;
        bar.style.background = this.thresholdColor(percent);
        subEl.textContent = sub;
    }

    /**
     * Map a percentage to its threshold color CSS variable
     */
    thresholdColor(percent) {
        if (percent >= 90) return 'var(--red)';
        if (percent >= 70) return 'var(--amber)';
        return 'var(--green)';
    }

    /**
     * Format bytes to human-readable format
     */
    formatBytes(bytes, decimals = 1) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];

        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
}

// Initialize widget when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const metricsWidget = new MetricsWidget(1000); // Update every 1 second
    metricsWidget.init();
});
