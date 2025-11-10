# -*- coding: utf-8 -*-
"""
MonitoringSkill

This skill provides real-time system monitoring and diagnostics,
addressing Phase 1.2 of the Sebas Evolution Plan.
"""

import os
import psutil
import logging
import time
from typing import Optional
from .base_skill import BaseSkill

class MonitoringSkill(BaseSkill):
    """
    Skill for monitoring system performance, network, and hardware.
    """
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'get_system_performance',
            'get_network_stats',
            'get_disk_io',
            'get_temperatures',
            'check_disk_space',
            'run_disk_cleanup',
            'check_memory_leaks',
            'analyze_startup_impact',
            'disable_startup_item'
        ]
        self.disk_space_threshold = self.assistant.prefs.get_pref('disk_space_threshold_percent', 85.0)
        # Cache for startup items
        self.startup_items_cache = []

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def get_intents(self) -> list:
        return self.intents

    def handle(self, intent: str, slots: dict) -> bool:
        if intent == 'get_system_performance':
            self.get_system_performance()
            return True
        if intent == 'get_network_stats':
            self.get_network_stats()
            return True
        if intent == 'get_disk_io':
            self.get_disk_io()
            return True
        if intent == 'get_temperatures':
            self.get_temperatures()
            return True
        if intent == 'check_disk_space':
            self.check_disk_space()
            return True
        if intent == 'run_disk_cleanup':
            self.assistant.run_disk_cleanup()
            return True
        if intent == 'check_memory_leaks':
            self.check_memory_leaks()
            return True
        if intent == 'analyze_startup_impact':
            self.analyze_startup_impact()
            return True
        if intent == 'disable_startup_item':
            item_name = slots.get('item_name')
            if item_name is None:
                self.assistant.speak("Please specify which startup log item to disable.")
                return False
            self.disable_startup_item(item_name)
            return True
        return False

    def get_system_performance(self):
        """Reports on CPU and Memory usage."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            self.assistant.speak(f"Current CPU utilization is at {cpu_usage:.1f} percent. "
                                 f"Memory usage is at {mem.percent} percent.")
        except Exception:
            logging.exception("Failed to get system performance.")
            self.assistant.speak("I was unable to retrieve system performance metrics.")

    def get_network_stats(self):
        """Reports on network connections."""
        try:
            connections = psutil.net_connections()
            listening = 0
            established = 0
            for conn in connections:
                if conn.status == 'LISTEN':
                    listening += 1
                elif conn.status == 'ESTABLISHED':
                    established += 1
            
            self.assistant.speak(f"There are currently {established} established network connections and {listening} listening ports.")
        except Exception:
            logging.exception("Failed to get network stats.")
            self.assistant.speak("I was unable to retrieve network statistics.")

    def get_disk_io(self):
        """Reports on disk I/O."""
        try:
            io = psutil.disk_io_counters()
            if io is not None:
                read_mb = io.read_bytes / (1024 * 1024)
                write_mb = io.write_bytes / (1024 * 1024)
                self.assistant.speak(f"Disk activity since boot: {read_mb:.1f} megabytes read, and {write_mb:.1f} megabytes written.")
            else:
                self.assistant.speak("I was unable to retrieve disk activity.")
        except Exception:
            logging.exception("Failed to get disk I/O.")
            self.assistant.speak("I was unable to retrieve disk activity.")

    def get_temperatures(self):
        """Reports on hardware temperatures."""
        try:
            sensors_temps = getattr(psutil, 'sensors_temperatures', None)
            if not sensors_temps:
                self.assistant.speak("I'm sorry, I cannot read temperature sensors on this system.")
                return

            temps = sensors_temps()
            if not temps:
                self.assistant.speak("No temperature sensors were found.")
                return

            # Prioritize coretemp for CPU, then find the first available reading
            # This is a common pattern as psutil returns a dict of lists of sensor readings
            cpu_temps = temps.get('coretemp', [])
            if cpu_temps:
                avg_temp = sum(t.current for t in cpu_temps) / len(cpu_temps)
                self.assistant.speak(f"The average CPU core temperature is {avg_temp:.0f} degrees Celsius.")
            else:
                # Fallback to the first sensor found
                for name, entries in temps.items():
                    if entries:
                        self.assistant.speak(f"The {name} temperature is {entries[0].current:.0f} degrees Celsius.")
                        return
        except Exception:
            logging.exception("Failed to get temperatures.")
            self.assistant.speak("I was unable to retrieve hardware temperatures.")

    def check_disk_space(self):
        """Reports on disk space usage for the primary drive."""
        try:
            # Check the drive where the OS is installed
            path = os.getenv('SystemDrive', 'C:\\')
            usage = psutil.disk_usage(path)
            
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            
            self.assistant.speak(f"The main drive has {free_gb:.1f} gigabytes free out of {total_gb:.1f} gigabytes. "
                                 f"Usage is at {usage.percent} percent.")
            
            if usage.percent > self.disk_space_threshold:
                self.assistant.speak("Disk space is running low. Would you like me to run a disk cleanup?")
                # The user can then say "yes" or "run disk cleanup"

        except Exception:
            logging.exception("Failed to check disk space.")
            self.assistant.speak("I was unable to check the disk space.")

    def check_memory_leaks(self, duration_seconds=30, growth_threshold_mb=50):
        """
        Monitors processes for a short duration to detect potential memory leaks.
        A "leak" is defined as significant memory growth over the sampling period.
        """
        self.assistant.speak(f"I will monitor system memory for {duration_seconds} seconds to detect potential leaks. Please wait.")
        
        try:
            # Initial snapshot
            initial_snapshot = {p.pid: p.info for p in psutil.process_iter(['pid', 'name', 'memory_info']) if p.info.get('memory_info')}
            
            time.sleep(duration_seconds)
            
            # Final snapshot
            final_snapshot = {p.pid: p.info for p in psutil.process_iter(['pid', 'name', 'memory_info']) if p.info.get('memory_info')}
            
            leaky_processes = []
            for pid, final_info in final_snapshot.items():
                if pid in initial_snapshot:
                    initial_rss = initial_snapshot[pid]['memory_info'].rss
                    final_rss = final_info['memory_info'].rss
                    growth_mb = (final_rss - initial_rss) / (1024 * 1024)
                    
                    if growth_mb > growth_threshold_mb:
                        leaky_processes.append({
                            'name': final_info['name'],
                            'pid': pid,
                            'growth_mb': growth_mb
                        })
            
            if not leaky_processes:
                self.assistant.speak("No significant memory growth was detected during the monitoring period.")
                return

            leaky_processes.sort(key=lambda x: x['growth_mb'], reverse=True)
            top_leaker = leaky_processes[0]
            self.assistant.speak(f"The process '{top_leaker['name']}' has grown by {top_leaker['growth_mb']:.0f} megabytes. This could indicate a memory leak.")
            
            if self.assistant.confirm_action(f"Would you like me to terminate the '{top_leaker['name']}' process?"):
                self.assistant.kill_process(str(top_leaker['pid']))
            else:
                self.assistant.speak("Very well. I will not terminate the process.")

        except Exception:
            logging.exception("Failed to check for memory leaks.")
            self.assistant.speak("I encountered an error while checking for memory leaks.")

    def analyze_startup_impact(self):
        """Analyzes and lists applications that run on startup."""
        self.assistant.speak("Analyzing startup applications. This may take a moment.")
        success, response = self.assistant.service_client.send_command('get_startup_items')

        if not success:
            self.assistant.speak(f"I was unable to retrieve startup items. {response}")
            return

        items = response.get('items', [])
        self.startup_items_cache = items

        if not items:
            self.assistant.speak("No startup applications were found in common locations.")
            return

        item_names = [item['name'] for item in items]
        # Speak only the top few for brevity
        spoken_items = item_names[:5]
        
        self.assistant.speak(f"I found {len(item_names)} startup items. Some of them are: {', '.join(spoken_items)}.")
        self.assistant.speak("You can ask me to disable any of them by name.")

    def disable_startup_item(self, item_name: Optional[str]):
        """Disables a specific startup item."""
        if not item_name:
            self.assistant.speak("Please specify which startup item to disable.")
            return

        item_to_disable = next((item for item in self.startup_items_cache if item_name.lower() in item['name'].lower()), None)

        if not item_to_disable:
            self.assistant.speak(f"I could not find a startup item named '{item_name}'. Please run the startup analysis again.")
            return

        if self.assistant.confirm_action(f"Are you sure you want to disable {item_to_disable['name']} from starting up?"):
            success, response = self.assistant.service_client.send_command('disable_startup_item', {'item': item_to_disable})
            if success:
                self.assistant.speak(f"{item_to_disable['name']} has been disabled.")
            else:
                self.assistant.speak(f"Failed to disable {item_to_disable['name']}. {response}")
        else:
            self.assistant.speak("Action cancelled.")