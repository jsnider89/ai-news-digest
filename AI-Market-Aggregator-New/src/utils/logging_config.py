# src/utils/logging_config.py
import logging
import os
from typing import Optional

def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up secure logging that doesn't leak API keys
    """
    logger = logging.getLogger("market_aggregator")
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        
        # Custom formatter that masks sensitive data
        class SecureFormatter(logging.Formatter):
            def format(self, record):
                # Mask any potential API keys in log messages
                if hasattr(record, 'msg') and isinstance(record.msg, str):
                    # Replace any long alphanumeric strings that might be API keys
                    import re
                    record.msg = re.sub(r'\b[A-Za-z0-9]{20,}\b', '[REDACTED]', record.msg)
                return super().format(record)
        
        formatter = SecureFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper()))
    
    return logger

def validate_environment() -> dict:
    """
    Validate all required environment variables are present
    Returns dict of missing variables for clear error reporting
    """
    required_vars = {
        'email': ['SENDER_EMAIL', 'SENDER_PASSWORD', 'RECIPIENT_EMAIL'],
        'apis': ['FINNHUB_API_KEY'],
        'ai': ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY']  # At least one required
    }
    
    missing = {}
    
    for category, vars_list in required_vars.items():
        missing_in_category = []
        for var in vars_list:
            if not os.getenv(var):
                missing_in_category.append(var)
        
        if category == 'ai':
            # For AI, we only need one of the APIs
            if all(not os.getenv(var) for var in vars_list):
                missing['ai'] = 'At least one of: ' + ', '.join(vars_list)
        elif missing_in_category:
            missing[category] = missing_in_category
    
    return missing
