from sec_edgar_downloader import Downloader

d1 = Downloader("Salman", "mohammadsalman17052006@gmail.com", "data/raw")

companies = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

for ticker in companies:
    print(f"Downloading {ticker}...")
    d1.get("10-K", ticker, limit = 2 , download_details = True)

print("Done!!!")