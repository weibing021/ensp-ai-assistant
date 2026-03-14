import textfsm
import os
import logging

logger = logging.getLogger(__name__)

class CLIParser:
    def __init__(self, template_dir="templates"):
        self.template_dir = template_dir

    def parse_with_textfsm(self, output, template_name):
        template_path = os.path.join(self.template_dir, template_name)
        if not os.path.exists(template_path):
            logger.error(f"Template {template_name} not found")
            return None
        
        with open(template_path) as f:
            re_table = textfsm.TextFSM(f)
            result = re_table.ParseText(output)
            # Convert list of lists to list of dicts
            header = re_table.header
            return [dict(zip(header, row)) for row in result]
