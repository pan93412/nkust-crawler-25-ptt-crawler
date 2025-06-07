#!/usr/bin/env python3
"""
PTT Scraper - Legacy entry point

This file provides backward compatibility with the old interface.
For new usage, please use: python -m ptt_scraper.main
"""

from src.ptt_scraper.main import interactive_mode


def main():
    """Legacy main function for backward compatibility"""
    print("⚠️  This is the legacy entry point.")
    print("For better experience, please use: python -m ptt_scraper.main --help")
    print("Falling back to interactive mode...\n")
    
    interactive_mode()


if __name__ == "__main__":
    main()
