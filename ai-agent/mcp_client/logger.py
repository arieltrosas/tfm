# mcp_client/logger.py
import logging
import json
import datetime

class IndentedJsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "event_type": getattr(record, "event_type", "generic_log"),
            "model_used": getattr(record, "model_used", "unknown"),
            "data": record.msg
        }
        return json.dumps(log_record, indent=2, default=str)

def setup_client_logger(log_file: str = "mcp_client.log"):
    logger = logging.getLogger("mcp_client_logger")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(IndentedJsonFormatter())
        logger.addHandler(file_handler)
        
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        console.setLevel(logging.WARNING) 
        logger.addHandler(console)
        
    return logger
