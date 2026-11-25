"""Stock research tools shared by the notebooks and the final project."""
import yfinance as yf
from langchain.tools import tool


@tool
def search_ticker(company_name: str) -> str:
    """Find the stock ticker symbol for a company name like 'Apple' or 'Tesla'.
    Always use this first when the user gives a company name instead of a ticker."""
    results = yf.Search(company_name, max_results=6, news_count=0).quotes
    stocks = [q for q in results if q.get("quoteType") == "EQUITY"]
    if not stocks:
        return f"No stock found for '{company_name}'."
    return "\n".join(f"{q['symbol']}: {q.get('shortname')} ({q.get('exchange')})" for q in stocks)


@tool
def get_snapshot(ticker: str) -> str:
    """Get current price and key numbers for a stock ticker like AAPL:
    price, P/E ratio, market cap, sector, 52-week range."""
    info = yf.Ticker(ticker).info
    keys = ["longName", "sector", "currentPrice", "currency", "trailingPE", "forwardPE",
            "marketCap", "fiftyTwoWeekLow", "fiftyTwoWeekHigh", "recommendationKey"]
    return "\n".join(f"{k}: {info.get(k)}" for k in keys)


def _trend(symbol: str, period: str) -> str:
    close = yf.Ticker(symbol).history(period=period)["Close"]
    if close.empty:
        return f"No price data for {symbol}."
    start, end = close.iloc[0], close.iloc[-1]
    return (f"{symbol} over {period}: start ${start:.2f}, end ${end:.2f}, "
            f"change {100 * (end - start) / start:+.1f}%, high ${close.max():.2f}, low ${close.min():.2f}")


@tool
def get_price_trend(ticker: str, period: str = "6mo") -> str:
    """Get how a stock's price changed over a period. Period is one of:
    1mo, 3mo, 6mo, 1y, 5y. Returns start, end, change in percent, high and low."""
    return _trend(ticker, period)


@tool
def get_market_trend(period: str = "6mo") -> str:
    """Get how the whole US market (S&P 500) changed over a period. Use it to compare a stock
    against the market. Period is one of: 1mo, 3mo, 6mo, 1y, 5y. Use the same period as the stock."""
    return _trend("^GSPC", period)


@tool
def get_recent_news(ticker: str) -> str:
    """Get the latest news headlines for a stock ticker like AAPL."""
    lines = []
    for item in yf.Ticker(ticker).news[:5]:
        c = item.get("content", item)
        lines.append(f"- {c.get('title')} ({c.get('pubDate', '')[:10]})")
    return "\n".join(lines) or "No recent news."


ALL_TOOLS = [search_ticker, get_snapshot, get_price_trend, get_market_trend, get_recent_news]
