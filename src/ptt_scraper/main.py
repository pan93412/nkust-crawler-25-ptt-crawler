#!/usr/bin/env python3
"""
PTT Scraper - Main entry point

Usage examples:
    python -m ptt_scraper.main --board Gossiping --keyword 政治
    python -m ptt_scraper.main --board TechJob --keyword 軟體工程師 --max-articles 50
"""

import asyncio
import argparse
import sys

from .crawler import crawl_ptt
from .database import DatabaseManager


def parse_args() -> argparse.Namespace:
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description="PTT Scraper - 爬取 PTT 文章和留言",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--board", 
        required=True,
        help="PTT 看板名稱 (如: Gossiping, TechJob)"
    )
    
    parser.add_argument(
        "--keyword",
        required=True, 
        help="搜尋關鍵字"
    )
    
    parser.add_argument(
        "--db-path",
        default="ptt_scraper.db",
        help="資料庫檔案路徑 (預設: ptt_scraper.db)"
    )
    
    parser.add_argument(
        "--cutoff-days",
        type=int,
        default=5,
        help="只抓取幾天內的文章 (預設: 5)"
    )
    
    parser.add_argument(
        "--max-articles",
        type=int,
        help="最大文章數量限制"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="顯示資料庫統計資訊並退出"
    )
    
    return parser.parse_args()


def show_stats(db_path: str) -> None:
    """顯示資料庫統計資訊"""
    db_manager = DatabaseManager(db_path)
    try:
        stats = db_manager.get_database_stats()
        print("\n=== PTT Scraper 資料庫統計 ===")
        print(f"總文章數: {stats.total_articles}")
        print(f"總留言數: {stats.total_comments}")
        print(f"資料庫檔案: {stats.database_path}")
        print(f"資料庫大小: {stats.database_size_mb} MB")
        print("=" * 32)
    finally:
        db_manager.close()


async def main() -> None:
    """主程式進入點"""
    args = parse_args()
    
    # 如果只是要顯示統計資訊
    if args.stats:
        show_stats(args.db_path)
        return
    
    # 驗證參數
    if not args.board or not args.keyword:
        print("錯誤: 必須提供看板名稱和搜尋關鍵字", file=sys.stderr)
        sys.exit(1)
    
    print(f"開始爬取 PTT 看板: {args.board}")
    print(f"搜尋關鍵字: {args.keyword}")
    print(f"資料庫檔案: {args.db_path}")
    print(f"時間限制: 最近 {args.cutoff_days} 天")
    if args.max_articles:
        print(f"文章數量限制: {args.max_articles}")
    print("-" * 50)
    
    try:
        # 執行爬蟲
        processed_count = await crawl_ptt(
            board=args.board,
            keyword=args.keyword,
            db_path=args.db_path,
            cutoff_days=args.cutoff_days,
            max_articles=args.max_articles
        )
        
        print(f"\n🎉 爬取完成！成功處理了 {processed_count} 篇文章")
        
        # 顯示最終統計
        show_stats(args.db_path)
        
    except KeyboardInterrupt:
        print("\n⚠️ 爬取被使用者中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 爬取過程中發生錯誤: {e}", file=sys.stderr)
        sys.exit(1)


def interactive_mode() -> None:
    """互動模式"""
    print("=== PTT Scraper 互動模式 ===")
    
    try:
        board = input("請輸入看板名稱: ").strip()
        keyword = input("請輸入搜尋關鍵字: ").strip()
        
        if not board or not keyword:
            print("錯誤: 看板名稱和關鍵字不能為空")
            return
        
        # 執行爬蟲
        _ = asyncio.run(crawl_ptt(board, keyword))
        
    except KeyboardInterrupt:
        print("\n⚠️ 程式被使用者中斷")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")


if __name__ == "__main__":
    # 如果沒有命令列參數，啟動互動模式
    if len(sys.argv) == 1:
        interactive_mode()
    else:
        asyncio.run(main()) 