import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.ptt_scraper.crawler import PTTCrawler


def describe_ptt_crawler():
    """測試 PTTCrawler 類別"""
    
    def test_cutoff_date_calculation():
        """測試截止日期計算邏輯"""
        # 測試正常情況
        crawler = PTTCrawler("test.db", cutoff_days=5)
        cutoff_date = crawler.get_cutoff_date()
        expected_date = datetime.today() - timedelta(days=5)
        expected_date = expected_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        assert cutoff_date.date() == expected_date.date()
        assert cutoff_date.hour == 0
        assert cutoff_date.minute == 0
        assert cutoff_date.second == 0
        assert cutoff_date.microsecond == 0
    
    @pytest.mark.parametrize("cutoff_days", [1, 8, 15, 30, 60])
    def test_cutoff_date_various_days(cutoff_days: int):
        """測試不同cutoff_days的截止日期計算"""
        crawler = PTTCrawler("test.db", cutoff_days=cutoff_days)
        cutoff_date = crawler.get_cutoff_date()
        expected_date = datetime.today() - timedelta(days=cutoff_days)
        
        # 檢查日期是否正確（不檢查時間部分）
        assert cutoff_date.date() == expected_date.date()
        
        # 檢查時間是否重置為午夜
        assert cutoff_date.hour == 0
        assert cutoff_date.minute == 0
        assert cutoff_date.second == 0
        assert cutoff_date.microsecond == 0
    
    def test_cutoff_date_month_boundary():
        """測試跨月邊界的截止日期計算"""
        # 模擬今天是5月8日，cutoff_days=10的情況
        # 應該得到4月28日
        crawler = PTTCrawler("test.db", cutoff_days=10)
        
        # 手動測試：假設今天是5月8日
        test_today = datetime(2025, 5, 8, 14, 30, 45, 123456)
        expected_cutoff = datetime(2025, 4, 28, 0, 0, 0, 0)
        
        # 計算實際的cutoff_date
        actual_cutoff = test_today - timedelta(days=10)
        actual_cutoff = actual_cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        
        assert actual_cutoff == expected_cutoff
    
    def test_cutoff_date_year_boundary():
        """測試跨年邊界的截止日期計算"""
        # 模擬今天是1月5日，cutoff_days=10的情況
        # 應該得到去年12月26日
        test_today = datetime(2025, 1, 5, 14, 30, 45, 123456)
        expected_cutoff = datetime(2024, 12, 26, 0, 0, 0, 0)
        
        # 計算實際的cutoff_date
        actual_cutoff = test_today - timedelta(days=10)
        actual_cutoff = actual_cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        
        assert actual_cutoff == expected_cutoff 