import logging
import os

def setup_logger(name: str) -> logging.Logger:
    """Configures global logging standards."""
    logger = logging.getLogger(name)
    
    # Avoid attaching multiple root handlers if already instantiated by uvicorn
    if not logger.handlers:
        level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
        logger.setLevel(level)

        handler = logging.StreamHandler()
        handler.setLevel(level)

        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

def mask_phone(number: str) -> str:
    """
    Masks PII phone numbers preserving only 3 prefix and 2 suffix digits.
    Eg: `1234567890` -> `123****90`
    """
    if not number:
        return "UNKNOWN"
        
    s = str(number)
    if len(s) < 6:
        return "****"
        
    return f"{s[:3]}****{s[-2:]}"
