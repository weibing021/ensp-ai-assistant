import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir

    def generate_json_report(self, task_name, task_result, status):
        report = {
            "task": task_name,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "result": task_result
        }
        filename = f"{task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(f"{self.data_dir}/{filename}", "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report generated: {filename}")

    def generate_text_report(self, task_name, task_result):
        report_str = f"Task: {task_name}\nTimestamp: {datetime.now()}\nResult: {task_result}"
        filename = f"{task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(f"{self.data_dir}/{filename}", "w") as f:
            f.write(report_str)
        logger.info(f"Report generated: {filename}")
