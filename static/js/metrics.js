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
        // CPU Usage
        this.updateProgressBar('cpu-usage', data.cpu.usage);
        document.getElementById('cpu-usage-value').textContent = `${data.cpu.usage.toFixed(1)}%`;

        // Memory Usage
        this.updateProgressBar('memory-usage', data.memory.percent);
        document.getElementById('memory-usage-value').textContent = `${data.memory.percent.toFixed(1)}%`;
        document.getElementById('memory-details').textContent = 
            `${this.formatBytes(data.memory.used)} / ${this.formatBytes(data.memory.total)}`;

        // Disk Usage
        this.updateProgressBar('disk-usage', data.disk.percent);
        document.getElementById('disk-usage-value').textContent = `${data.disk.percent.toFixed(1)}%`;
        document.getElementById('disk-details').textContent = 
            `${this.formatBytes(data.disk.used)} / ${this.formatBytes(data.disk.total)}`;

        // GPU Information (if available)
        const gpuSection = document.getElementById('gpu-section');
        if (data.gpu.available && data.gpu.gpus.length > 0) {
            gpuSection.style.display = 'block';
            
            // Update each GPU
            data.gpu.gpus.forEach((gpu, index) => {
                const gpuId = `gpu-${index}`;
                
                // Create elements if they don't exist
                if (!document.getElementById(gpuId)) {
                    this.createGpuElements(index);
                }
                
                // Update values
                this.updateProgressBar(`${gpuId}-usage`, gpu.util_percent);
                document.getElementById(`${gpuId}-usage-value`).textContent = `${gpu.util_percent.toFixed(1)}%`;
                
                this.updateProgressBar(`${gpuId}-memory`, (gpu.memory_used / gpu.memory_total) * 100);
                document.getElementById(`${gpuId}-memory-value`).textContent = 
                    `${this.formatBytes(gpu.memory_used * 1024 * 1024)} / ${this.formatBytes(gpu.memory_total * 1024 * 1024)}`;
                
                const tempElement = document.getElementById(`${gpuId}-temp`);
                tempElement.textContent = `${gpu.temperature.toFixed(1)}°C`;
                this.updateTemperatureClass(tempElement, gpu.temperature);
            });
        } else {
            gpuSection.style.display = 'none';
        }

        // CPU Temperature (if available)
        const cpuTempContainer = document.getElementById('cpu-temp-container');
        if (data.cpu.temperature.available && data.cpu.temperature.sensors.length > 0) {
            cpuTempContainer.style.display = 'block';
            cpuTempContainer.innerHTML = ''; // Clear previous entries
            
            // Sort sensors by temperature (highest first)
            const sortedSensors = [...data.cpu.temperature.sensors].sort((a, b) => b.temp - a.temp);
            
            // Display up to 3 sensors with highest temps
            const sensorsToShow = sortedSensors.slice(0, 3);
            sensorsToShow.forEach(sensor => {
                const tempItem = document.createElement('div');
                tempItem.className = 'temperature-item';
                
                const label = document.createElement('span');
                label.className = 'temperature-label';
                label.textContent = sensor.type || sensor.zone;
                
                const value = document.createElement('span');
                value.className = 'temperature-value';
                value.textContent = `${sensor.temp.toFixed(1)}°C`;
                this.updateTemperatureClass(value, sensor.temp);
                
                tempItem.appendChild(label);
                tempItem.appendChild(value);
                cpuTempContainer.appendChild(tempItem);
            });
        } else {
            cpuTempContainer.style.display = 'none';
        }
    }

    /**
     * Update a progress bar with the given value
     */
    updateProgressBar(id, value) {
        const progressBar = document.getElementById(id);
        if (progressBar) {
            progressBar.style.width = `${value}%`;
            progressBar.setAttribute('aria-valuenow', value);
            
            // Update color based on value
            progressBar.className = 'progress-bar';
            if (value < 50) {
                progressBar.classList.add('bg-success');
            } else if (value < 80) {
                progressBar.classList.add('bg-warning');
            } else {
                progressBar.classList.add('bg-danger');
            }
        }
    }

    /**
     * Create UI elements for a GPU
     */
    createGpuElements(index) {
        const gpuContainer = document.getElementById('gpu-container');
        const gpuId = `gpu-${index}`;
        
        const gpuSection = document.createElement('div');
        gpuSection.className = 'metric-item';
        gpuSection.id = gpuId;
        
        // GPU Usage
        const usageLabel = document.createElement('div');
        usageLabel.className = 'metric-label';
        usageLabel.innerHTML = `GPU ${index} Usage <span id="${gpuId}-usage-value" class="metric-value">0%</span>`;
        
        const usageProgress = document.createElement('div');
        usageProgress.className = 'progress';
        usageProgress.innerHTML = `<div id="${gpuId}-usage" class="progress-bar bg-success" role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>`;
        
        // GPU Memory
        const memoryLabel = document.createElement('div');
        memoryLabel.className = 'metric-label';
        memoryLabel.innerHTML = `VRAM <span id="${gpuId}-memory-value" class="metric-value">0 MB / 0 MB</span>`;
        
        const memoryProgress = document.createElement('div');
        memoryProgress.className = 'progress';
        memoryProgress.innerHTML = `<div id="${gpuId}-memory" class="progress-bar bg-success" role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>`;
        
        // GPU Temperature
        const tempItem = document.createElement('div');
        tempItem.className = 'temperature-item';
        tempItem.innerHTML = `<span class="temperature-label">Temperature</span><span id="${gpuId}-temp" class="temperature-value temp-normal">0°C</span>`;
        
        // Add all elements to the container
        gpuSection.appendChild(usageLabel);
        gpuSection.appendChild(usageProgress);
        gpuSection.appendChild(memoryLabel);
        gpuSection.appendChild(memoryProgress);
        gpuSection.appendChild(tempItem);
        
        gpuContainer.appendChild(gpuSection);
    }

    /**
     * Update temperature element class based on value
     */
    updateTemperatureClass(element, temperature) {
        element.classList.remove('temp-normal', 'temp-warning', 'temp-danger');
        
        if (temperature < 60) {
            element.classList.add('temp-normal');
        } else if (temperature < 80) {
            element.classList.add('temp-warning');
        } else {
            element.classList.add('temp-danger');
        }
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
