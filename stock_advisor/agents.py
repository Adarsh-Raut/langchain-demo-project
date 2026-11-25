"""Sub-agents: small agents that each do one focused job for the main advisor."""
from pathlib import Path
from typing import Literal

import yfinance as yf
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from pydantic import BaseModel, Field

from stock_advisor.tools import (
    get_market_trend, get_price_trend, get_snapshot, search_ticker,
)

# The agents below are built the moment this file is imported, so the API key must be loaded first.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Groq's free tier allows about 8,000 tokens per minute. Sub-agents make many model calls, so we
# let the client wait and retry (max_retries) instead of crashing on the first "rate limit" reply.
MODEL = init_chat_model("groq:openai/gpt-oss-120b", max_retries=8)

# Raw tool results from the researcher. The reviewer later checks the final answer against these.
EVIDENCE: list[str] = []


# ---------------------------------------------------------------- 1. News checker
class NewsVerdict(BaseModel):
    relevant_numbers: list[int] = Field(description="Numbers of the headlines that are really about this company")
    reason: str = Field(description="One short sentence explaining the choice")


news_checker = create_agent(
    model=MODEL,
    tools=[],
    system_prompt=(
        "You check news headlines for one company. Keep a headline only if the company itself is "
        "the subject or is directly affected by the story. Drop headlines about other companies, "
        "general market roundups, and 'top stock picks' lists. If none qualify, return an empty list."
    ),
    response_format=NewsVerdict,
)


@tool
def get_relevant_news(ticker: str) -> str:
    """Get recent news that is actually about the company behind a ticker like AAPL.
    A checking sub-agent removes off-topic headlines first."""
    t = yf.Ticker(ticker)
    items = [item.get("content", item) for item in t.news[:10]]
    if not items:
        return "No recent news."
    company = t.info.get("longName", ticker)
    lines = [f"{i}. {c.get('title')} - {(c.get('summary') or '')[:200]}" for i, c in enumerate(items, 1)]
    prompt = f"Company: {company} (ticker {ticker})\nHeadlines:\n" + "\n".join(lines)
    verdict = news_checker.invoke({"messages": [{"role": "user", "content": prompt}]})["structured_response"]
    keep = [n for n in verdict.relevant_numbers if 1 <= n <= len(items)]
    if not keep:
        return f"Checked {len(items)} headlines. None are about {company}. ({verdict.reason})"
    shown = [f"- {items[n - 1].get('title')} ({items[n - 1].get('pubDate', '')[:10]})" for n in keep]
    return f"{len(keep)} of {len(items)} headlines are about {company}:\n" + "\n".join(shown)


# ---------------------------------------------------------------- 2. Researcher
RESEARCHER_TOOLS = [search_ticker, get_snapshot, get_price_trend, get_market_trend, get_relevant_news]

researcher = create_agent(
    model=MODEL,
    tools=RESEARCHER_TOOLS,
    system_prompt=(
        "You are a stock researcher. You are given a company name, not a ticker. "
        "Find the ticker, then get the snapshot, the price trend, the market trend over the same period, "
        "and the news. Report facts only, in under 200 words.\n"
        "Rules: only state numbers that appear in a tool result; only compare with the market if you "
        "have both numbers; if you lack data, say 'no data'. Never add general market knowledge."
    ),
)


@tool
def research_company(request: str) -> str:
    """Hand a research job to the researcher sub-agent. Give it a company name and what to find out,
    for example 'Apple: price, 6 month trend versus the market, and recent news'.
    Returns a short fact-only report."""
    result = researcher.invoke({"messages": [{"role": "user", "content": request}]})
    EVIDENCE.extend(m.content for m in result["messages"] if m.type == "tool")
    return result["messages"][-1].content


# ---------------------------------------------------------------- 3. Reviewer
class ReviewReport(BaseModel):
    verdict: Literal["pass", "fail"]
    unsupported_claims: list[str] = Field(description="Claims in the answer that the evidence does not support")


reviewer = create_agent(
    model=MODEL,
    tools=[],
    system_prompt=(
        "You are a strict fact checker. You get EVIDENCE (tool results) and an ANSWER.\n"
        "List every specific number, comparison, or factual claim in the ANSWER that the EVIDENCE does "
        "not support. Examples: a dividend yield, an 'average P/E', 'outperformed the market' without "
        "market numbers, a price that differs from the evidence.\n"
        "Arithmetic on numbers that ARE in the evidence is fine. Disclaimers are fine. "
        "If nothing is unsupported, verdict is 'pass' with an empty list. Otherwise verdict is 'fail'."
    ),
    response_format=ReviewReport,
)


def review(answer: str, evidence: list[str]) -> ReviewReport:
    """Check an answer against the raw tool results."""
    prompt = "EVIDENCE:\n" + "\n---\n".join(evidence) + "\n\nANSWER:\n" + answer
    return reviewer.invoke({"messages": [{"role": "user", "content": prompt}]})["structured_response"]
