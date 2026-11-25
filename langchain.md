# LangChain: Learning Notes

All my notes live in this one file. Each lesson has a matching notebook in `notebooks/`, where you can run one cell at a time.

## How to use this folder

1. Read a lesson here.
2. Open the matching notebook and run the cells one by one (`Shift+Enter`).
3. Change things and break them. That is how you learn.

### Setup (do this once)

```bash
cd ~/projects/langchain-learn
source .venv/bin/activate          # turn on the project's Python environment
cp .env.example .env               # then open .env and paste your API key
jupyter lab                        # opens the notebook interface in your browser
```

**Using VS Code instead?** Open `notebooks/01_basics.ipynb`, click "Select Kernel", and pick `.venv`. You get the same run-a-cell experience.

**Which model provider?** We use Groq through the `langchain-groq` package, so you need a `GROQ_API_KEY` (get one at https://console.groq.com/keys). We use the model `openai/gpt-oss-120b`, which supports tools. If Groq retires that model, pick another tool-capable one from their model list and change the name in one place. LangChain can use other providers too. Only the model name and the key change. Everything else stays the same.

---

## Roadmap

| # | Lesson | You will learn | Notebook |
|---|--------|----------------|----------|
| 1 | The basics | Models, messages, tools, your first agent | `01_basics.ipynb` |
| 2 | Tools with real data | Name-to-ticker search, prices, trends, news | `02_tools.ipynb` |
| 3 | Memory | Making the agent remember a conversation | `03_memory.ipynb` |
| 4 | Human-in-the-loop | Pausing the agent so a person can approve an action | *(next)* |
| 5 | Sub-agents | One agent that hands tasks to other agents | *(next)* |
| 6 | Context | Giving the agent files and user details | *(next)* |
| 7 | Final project | The stock advisor, run from the terminal | `stock_advisor/` |

---

## Lesson 1: The basics

### The four ideas you need

1. **Model.** The language model (the "brain"). You send it text and it sends text back. It cannot do anything else by itself. It cannot look up a stock price.
2. **Message.** One piece of a conversation. Messages have a role: `system` (your instructions), `human` (the user), `ai` (the model's reply), and `tool` (the result of a tool).
3. **Tool.** A normal Python function the model is allowed to ask for. The model does not run the function. It says "please call `get_price` with `AAPL`", and your code runs it and sends back the result.
4. **Agent.** A loop built from the three ideas above:
   1. The model reads the conversation.
   2. It either answers, or asks for a tool.
   3. If it asks for a tool, the tool runs and the result is added to the conversation.
   4. Go back to step 1. Stop when the model answers.

That loop is all an agent is. LangChain's `create_agent` builds it for you.

### Calling a model

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("groq:openai/gpt-oss-120b")
reply = model.invoke("What is a stock, in one sentence?")
print(reply.content)
```

`invoke` means "run this once and give me the answer".

### Making a tool

```python
from langchain.tools import tool

@tool
def get_price(ticker: str) -> str:
    """Get the latest price of a stock. Input is a ticker symbol like AAPL."""
    return f"{ticker} costs $100"   # fake data for now
```

Two things matter here:
- The **docstring** (the text in triple quotes) is shown to the model. It is how the model decides when to use the tool. Write it clearly.
- The **type hints** (`ticker: str`) tell the model what input to send.

### Making an agent

```python
from langchain.agents import create_agent

agent = create_agent(
    model="groq:openai/gpt-oss-120b",
    tools=[get_price],
    system_prompt="You are a careful stock research assistant.",
)

result = agent.invoke({"messages": [{"role": "user", "content": "How much is AAPL?"}]})
print(result["messages"][-1].content)
```

`result["messages"]` is the whole conversation, including the tool request and tool result. Print all of it once to watch the loop happen.

### Exercise

Add a second tool, `get_company_name(ticker)`, and ask the agent: "What is AAPL and how much is it?" Check that it calls both tools.

---

## Lesson 2: Tools with real stock data

Notebook: `notebooks/02_tools.ipynb`

### The problem

A real user says "I want to look into Apple", not "AAPL". The model cannot know the right ticker for sure, and it cannot fetch live data. So we give the agent tools, and the agent decides the order.

### The tool chain

```
User: "Is Apple doing well?"
   |
   v
search_ticker("Apple")        -> AAPL
   |
   v
get_snapshot("AAPL")          -> price, P/E, market cap
get_price_trend("AAPL","6mo") -> +15% over 6 months
get_market_trend("6mo")       -> S&P 500: -4.2% over 6 months
get_recent_news("AAPL")       -> headlines
   |
   v
Agent writes the answer using only those results
```

You never write this order in code. The agent works it out from each tool's docstring and from the system prompt.

### Rules for good tools

1. **Say when to use it.** `search_ticker` says "Always use this first when the user gives a company name". That one sentence is what makes the agent call it first.
2. **Return a short summary, not raw data.** `get_price_trend` returns start, end, change and high/low. It does not return 126 rows. Less data is cheaper and easier for the model to read.
3. **Return text that explains failures.** If nothing is found, return `"No stock found for 'X'"`. The agent can then try something else. If you crash instead, the whole run stops.
4. **Optional inputs get defaults.** `period: str = '6mo'` means the agent can skip it.

### Where the data comes from

We use the `yfinance` library, which reads public Yahoo Finance data. It needs no API key. It is unofficial and can break or be rate-limited, which is fine for learning. A real product would pay for a proper data provider.

### Something to notice

When we tested it, `get_recent_news` returned headlines that were about the market in general, not only Apple (for example, a headline about Xiaomi). The agent listed them anyway. This is a real problem for our project, because the user wants *evidence*. Evidence must be about the right company. We will fix this in a later lesson by having a separate "news checker" sub-agent that throws away headlines that are not relevant.

### Fixing made-up claims

In our first test the agent said Apple was "outperforming many broader market indices". No tool had given it market data, so it invented the claim. We fixed it in two ways:

1. **A tool for the missing data.** `get_market_trend` returns the S&P 500 change over the same period. Now the agent can compare: Apple +15.0% against the market -4.2%.
2. **Strict rules in the system prompt.** Only state numbers that came from a tool, only compare when you have both numbers, and say "I don't have data" instead of guessing.

After the fix, the agent made the comparison from real numbers. It also said no news was Apple-specific. It still listed the unrelated headlines, so the prompt rule helps but does not fully solve the news problem. A sub-agent will handle that later.

**Lesson:** a prompt rule reduces made-up claims, but giving the agent the data it needs works better. Use both.

### If you get `model_not_found`

Groq changes its model list over time. Run Step 7 in the notebook to list the models your key can use, then change `MODEL` at the top of the notebook.

### Exercise

1. Ask about "Meta" or "Google". Which ticker did the agent pick?
2. Ask "Compare Nvidia and AMD". How many tool calls did it make?
3. Add `get_analyst_opinion(ticker)`, which returns `recommendationKey` and `targetMeanPrice` from `yf.Ticker(ticker).info`.

---

## Lesson 3: Memory

Notebook: `notebooks/03_memory.ipynb`

### The problem

Every `invoke` call starts from nothing. The model has no memory of its own. If you tell it "my budget is $5,000" and then ask "what is my budget?" in a new call, it has no idea. The second call never saw the first.

### The fix: a checkpointer and a thread id

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(model=MODEL, tools=[...], checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "alice"}}
agent.invoke({"messages": [...]}, config=config)
```

- A **checkpointer** saves the conversation after every step and sends the saved messages back to the model on the next call.
- A **thread id** is the name of one conversation. Same id means the same conversation. A different id means a fresh start. In a real app, each user (or each chat) gets its own thread id, and conversations never mix.

### What we proved in the notebook

| Test | Result |
|------|--------|
| No checkpointer, ask for the budget | "I don't have any information about your budget" |
| Checkpointer, same thread | "Your budget is $5,000" |
| Checkpointer, different thread | The new thread does not know the budget |
| Advisor: state budget once, then ask about Apple, then Tesla | It reused the $5,000 budget and low-risk preference each time |

### Two limits to know

1. `InMemorySaver` lives in the notebook's memory. Restart the kernel and the memory is gone. A real app uses a saver that writes to a database (LangGraph has SQLite and Postgres versions). Only the checkpointer line changes.
2. The whole conversation is sent to the model every time. Long conversations get slow, cost more, and eventually stop fitting in the model's context window. Lesson 6 deals with this.

### Code organisation

The tools now live in `stock_advisor/tools.py`. Notebooks import them with `from stock_advisor.tools import ALL_TOOLS`. This is the file the final project will use too, so we never copy the same code twice.

### Exercise

1. In Step 5, ask "What is my budget?" in a new thread id. Does it know?
2. Run `advisor.get_state(me)` after three questions and count the messages. Why so many? (Hint: tool calls and tool results are messages too.)
3. Restart the kernel, run Step 5 again, and ask the budget question. What happened to the memory?

---

## Videos and references

*(Add your links here. I will use them to shape the next lessons.)*

- Official docs: https://docs.langchain.com

---

## Questions and notes

*(Your own notes go here.)*
