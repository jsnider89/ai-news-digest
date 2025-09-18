# market_intelligence_main.py
"""
Refactored AI Market Intelligence System
This replaces the original ai_market_aggregator.py with a modular, secure design

Key Improvements:
- Modular architecture (separate modules for each concern)
- Secure logging (no API key leakage)
- Proper RSS parsing with feedparser (no regex vulnerabilities)
- Input sanitization and XSS protection
- Better error handling and monitoring
- Clean separation of concerns
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv

def main():
    """
    Main entry point for the refactored market intelligence system
    """
    # Load environment variables from .env file for local development
    # In a production/CI environment, these are set directly
    load_dotenv()

    try:
        # Import the orchestrator
        from src.orchestrator import MarketIntelligenceOrchestrator
        
        # Initialize and run the analysis
        orchestrator = MarketIntelligenceOrchestrator()
        results = orchestrator.run_analysis()
        
        # Exit with appropriate code
        if results['success']:
            print("✅ Market intelligence analysis completed successfully")
            sys.exit(0)
        else:
            print("❌ Market intelligence analysis failed")
            if results.get('errors'):
                for error in results['errors']:
                    print(f"   Error: {error}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
