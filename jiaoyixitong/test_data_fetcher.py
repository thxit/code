import sys
import os
sys.path.insert(0, 'd:/code/jiaoyixitong')

from data.fetcher import DataFetcher
from config.settings import get_config

def main():
    print("Testing data fetcher with multiple data sources...")
    
    config = get_config()
    fetcher = DataFetcher(config)
    
    # Test index data fetching
    print("\n=== Testing Index Data (000001) ===")
    try:
        df = fetcher.fetch_index_daily("000001", period=100)
        if df is not None and not df.empty:
            print(f"Success! Got {len(df)} rows")
            print(f"Columns: {list(df.columns)}")
            print(f"Latest date: {df['date'].iloc[-1]}")
            print(f"Latest close: {df['close'].iloc[-1]}")
        else:
            print("Failed to fetch index data")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test stock list fetching
    print("\n=== Testing Stock List ===")
    try:
        df = fetcher.fetch_stock_list()
        if df is not None and not df.empty:
            print(f"Success! Got {len(df)} stocks")
            print(f"Columns: {list(df.columns)[:10]}")
        else:
            print("Failed to fetch stock list")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test north flow
    print("\n=== Testing North Flow ===")
    try:
        df = fetcher.fetch_north_flow(period=30)
        if df is not None and not df.empty:
            print(f"Success! Got {len(df)} rows")
            print(f"Columns: {list(df.columns)}")
        else:
            print("Failed to fetch north flow")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test industry flow
    print("\n=== Testing Industry Flow ===")
    try:
        df = fetcher.fetch_industry_flow()
        if df is not None and not df.empty:
            print(f"Success! Got {len(df)} rows")
            print(f"Columns: {list(df.columns)[:10]}")
        else:
            print("Failed to fetch industry flow")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()