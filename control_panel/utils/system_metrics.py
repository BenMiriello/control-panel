#!/usr/bin/env python3

import psutil
import subprocess
import json
from pathlib import Path

def get_cpu_usage():
    """Get CPU usage as a percentage"""
    return psutil.cpu_percent(interval=0.1)

def get_memory_usage():
    """Get memory usage information"""
    mem = psutil.virtual_memory()
    return {
        'total': mem.total,
        'available': mem.available,
        'used': mem.used,
        'free': mem.free,
        'percent': mem.percent
    }

def get_disk_usage():
    """Get disk usage information"""
    root_disk = psutil.disk_usage('/')
    return {
        'total': root_disk.total,
        'used': root_disk.used,
        'free': root_disk.free,
        'percent': root_disk.percent
    }

def get_gpu_info():
    """Get GPU information using nvidia-smi if available"""
    try:
        # Try to get GPU information using nvidia-smi
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        gpu_data = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                util, mem_used, mem_total, temp = map(float, line.split(','))
                gpu_data.append({
                    'util_percent': util,
                    'memory_used': int(mem_used),
                    'memory_total': int(mem_total),
                    'temperature': temp
                })
        
        return {'available': True, 'gpus': gpu_data}
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Try AMD GPU info if Nvidia not available
        try:
            result = subprocess.run(
                ['rocm-smi', '--showuse', '--showmemuse', '--showtemp', '--json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the JSON output
            data = json.loads(result.stdout)
            gpu_data = []
            
            for gpu_id, gpu_info in data.items():
                if 'GPU use' in gpu_info and 'Memory use' in gpu_info and 'Temperature' in gpu_info:
                    gpu_data.append({
                        'util_percent': float(gpu_info['GPU use'].strip('%')),
                        'memory_used': int(gpu_info['Memory use']['used_memory']),
                        'memory_total': int(gpu_info['Memory use']['total_memory']),
                        'temperature': float(gpu_info['Temperature'].strip('°C'))
                    })
            
            return {'available': True, 'gpus': gpu_data}
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            # No GPU info available
            return {'available': False, 'gpus': []}

def get_cpu_temperature():
    """Get CPU temperature information if available"""
    try:
        # Try to read temperature from thermal zones
        temps = []
        thermal_dir = Path('/sys/class/thermal')
        
        if thermal_dir.exists():
            for zone in thermal_dir.glob('thermal_zone*'):
                try:
                    # Read temperature
                    with open(zone / 'temp', 'r') as f:
                        temp = int(f.read().strip()) / 1000  # Convert from millidegrees to degrees
                    
                    # Read type
                    with open(zone / 'type', 'r') as f:
                        zone_type = f.read().strip()
                    
                    temps.append({'zone': zone.name, 'type': zone_type, 'temp': temp})
                except (IOError, ValueError):
                    continue
        
        # If no temperatures found, try using lm-sensors
        if not temps:
            try:
                result = subprocess.run(
                    ['sensors', '-j'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                data = json.loads(result.stdout)
                for chip, values in data.items():
                    if 'Adapter' in chip:
                        continue
                    
                    for key, items in values.items():
                        if isinstance(items, dict) and any('input' in k for k in items.keys()):
                            for temp_key, temp_val in items.items():
                                if 'input' in temp_key:
                                    temps.append({
                                        'zone': chip,
                                        'type': key,
                                        'temp': temp_val
                                    })
            except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
                pass
        
        return {'available': bool(temps), 'sensors': temps}
    except Exception:
        return {'available': False, 'sensors': []}

def get_all_metrics():
    """Get all system metrics in a single call"""
    return {
        'cpu': {
            'usage': get_cpu_usage(),
            'temperature': get_cpu_temperature()
        },
        'memory': get_memory_usage(),
        'disk': get_disk_usage(),
        'gpu': get_gpu_info()
    }
