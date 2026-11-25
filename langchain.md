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
| 4 | Human-in-the-loop | Pausing the agent so a person can approve an action | `04_human_in_the_loop.ipynb` |
| 5 | Sub-agents | One agent that hands tasks to other agents | `05_sub_agents.ipynb` |
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

## Lesson 4: Human-in-the-loop

Notebook: `notebooks/04_human_in_the_loop.ipynb`

### The problem

An agent that can spend money must not do it alone. It can be wrong. In an early test, with no price tool, it guessed 11 shares of Apple for a $2,000 budget. That would have cost $3,894. A human looking at the order before it runs catches this.

### The idea

Some tools only **read** (search, prices, news). Some **change something** (buy). We let the read tools run freely and put a pause in front of the ones that change something.

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_agent(
    model=MODEL,
    tools=RESEARCH_TOOLS + TRADING_TOOLS,
    middleware=[HumanInTheLoopMiddleware(interrupt_on={"buy_stock": True})],
    checkpointer=InMemorySaver(),      # required: the agent must remember where it stopped
)
```

### What happens

```
User: "I have $2000. Buy as many Apple shares as I can afford."
   |
   v
agent searches the ticker, gets the price, calls calculate_shares     (runs freely)
   |
   v
agent calls buy_stock(AAPL, 5)  ---->  PAUSE. Nothing is bought yet.
   |
   v
You look at the order and the estimated cost, then choose:
   approve  -> buy_stock runs exactly as the agent asked
   edit     -> buy_stock runs with YOUR numbers (for example, 2 shares)
   reject   -> buy_stock never runs; the agent reads your reason
```

When the agent pauses, `invoke` returns a result with an `__interrupt__` key. To continue, you call `invoke` again with your decision:

```python
from langgraph.types import Command

agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)

# edit
{"type": "edit", "edited_action": {"name": "buy_stock", "args": {"ticker": "AAPL", "shares": 2}}}

# reject
{"type": "reject", "message": "I changed my mind."}
```

### Two new tools

- `calculate_shares(budget, price)` does the money math in Python. Language models are bad at arithmetic (in Lesson 3 one said 13 shares when only 12 fit). **The agent should never do money math itself.**
- `buy_stock(ticker, shares)` is a pretend broker. It writes to a list called `ORDERS`. No real money moves.

### What we tested

| Decision | Result |
|----------|--------|
| Approve | 5 AAPL shares bought for $1,770.35 |
| Edit to 2 shares | The agent asked for 5, and 2 were bought ($708.14) |
| Reject | No order was placed |

### Things to remember

1. **The pause is saved.** Because of the checkpointer, the agent can resume after you run other cells.
2. **Use a new thread id for each scenario.** A paused thread stays paused until you answer it.
3. **The price can move.** You see an estimate at the pause, but `buy_stock` fetches the price again when it runs.
4. **Gate actions, not reads.** Pausing on every tool would make the agent unusable.
5. **Nothing stops a silly edit.** If you edit to more shares than your budget allows, the order still goes through. A real app would also check the budget inside `buy_stock`. This is one of the exercise questions.
6. **Reject reasons are only a hint.** After a rejection the agent read our reason but still re-summarised its research instead of acknowledging the decision. Prompts steer an agent, they do not control it.

### Code organisation

`stock_advisor/tools.py` now has two lists: `RESEARCH_TOOLS` (read only) and `TRADING_TOOLS` (`calculate_shares`, `buy_stock`). `ALL_TOOLS` is still the research tools only, so the Lesson 3 notebook cannot buy anything by accident.

### Exercise

1. Run Step 8 and answer `n` with a reason such as "too risky for me". Does the agent's reply use your reason?
2. Run Step 8 again and answer `e` with a number too big for your budget. Nothing stops you. How would you prevent that?
3. Change `interrupt_on` to `{'buy_stock': True, 'get_snapshot': True}` and ask about Apple. Why would that be annoying in a real app?

---

## Lesson 5: Sub-agents

Notebook: `notebooks/05_sub_agents.ipynb`. Code: `stock_advisor/agents.py`.

### The problems

Two problems kept appearing in earlier lessons:
1. The news tool returned headlines that were **not about the company** (a Xiaomi story under Apple).
2. The agent stated **facts no tool gave it** (a dividend yield, an "average P/E").

### The idea

A **sub-agent** is a normal agent with one narrow job. The main agent hands work to it the same way it calls a tool: you wrap the sub-agent inside an ordinary `@tool` function.

```
You  ->  Advisor (manager)  ->  research_company  ->  Researcher (sub-agent)
                                                         |-> search_ticker, get_snapshot,
                                                         |   get_price_trend, get_market_trend
                                                         '-> get_relevant_news -> News checker (sub-agent)
                |
                '-> calculate_shares
                '-> buy_stock   (human approval, Lesson 4)
        then:  Reviewer (sub-agent) checks the final answer against the raw tool results
```

### The three sub-agents

| Sub-agent | Job | Tools it has |
|-----------|-----|--------------|
| **News checker** | Reads 10 headlines, keeps only those about the company | none |
| **Researcher** | Collects price, trend, market comparison and news, reports facts only | the five research tools |
| **Reviewer** | Reads the evidence and an answer, lists every unsupported claim | none |

### Structured output

The news checker and reviewer must answer in a fixed shape, because our code reads their answers. You do this with `response_format`:

```python
class NewsVerdict(BaseModel):
    relevant_numbers: list[int]
    reason: str

news_checker = create_agent(model=MODEL, tools=[], system_prompt="...", response_format=NewsVerdict)

verdict = news_checker.invoke({...})["structured_response"]   # a real NewsVerdict object
```

### Why split the work

- **The manager stays focused.** It sees a 150-word report, not pages of raw numbers.
- **Each agent follows a few rules well.** One agent with twenty rules follows them worse.
- **You can test and improve each piece alone.** We tested the reviewer by planting made-up claims.

### What we saw

| Test | Result |
|------|--------|
| News checker, Nvidia | Kept 4 of 10 headlines and dropped the unrelated ones (Dollar Tree, an S&P market preview) |
| News checker, Apple | Kept 2 of 10 |
| Reviewer on a clean answer | PASS |
| Reviewer on an answer with a planted 0.6% dividend and "average P/E of 22" | FAIL, and it named both claims |
| Asking about Apple's dividend yield and debt, which no tool returns | The advisor said "No data available" instead of inventing numbers |
| Revision loop with a fake failure report | The advisor rewrote its answer and dropped the flagged claim |

### Costs and limits

1. **Every sub-agent is extra model calls.** More time and more tokens. The full notebook takes about two minutes.
2. **Groq's free tier has two limits for this model: about 8,000 tokens per minute and 200,000 tokens per day.** Sub-agents use a lot of tokens (one full question can use 20,000 or more), so you can hit `429 rate_limit_exceeded`. We set `max_retries=8`, which covers the per-minute limit. The **daily** limit is different: waiting a few seconds does not help. Once it is used up, requests only trickle through until the allowance recovers, and a test run can crawl for many minutes. Run fewer cells per session, and do not rerun the whole notebook over and over.
3. **The checker and reviewer are language models too.** They sometimes keep a borderline headline ("Top Analyst Reports for Apple, Philip Morris & Intel") or pass a mild embellishment ("points to strong governance" from a headline that did not say that). They lower the risk. They do not remove it.
4. **The reviewer only sees what you give it.** That is why `research_company` saves the researcher's raw tool results in a list called `EVIDENCE`. Without that, the reviewer could not check the manager's claims.
5. **The key must be loaded first.** `agents.py` builds its agents the moment it is imported, so it loads `.env` itself. Otherwise you get a "GROQ_API_KEY must be set" error in a notebook.

### A mistake that got past the reviewer (and the fix)

The first version passed this answer: *"Recent articles highlight Microsoft's strong security posture ('Patchpocalypse' response)... reinforcing its reputation for stability."* The real headline was **"Microsoft declares a code red in the middle of a 'Patchpocalypse'"**. A code red during a patch crisis is a problem, not a strength. The answer turned bad news into good news, and the reviewer said PASS.

We traced it. The researcher quoted both headlines correctly. The **manager** agent then added its own spin. The reviewer, given the full, long evidence, sometimes let it through, even though it catches the same sentence when the evidence is short.

The fix has three parts, all prompt changes:
1. **Researcher:** copy headlines exactly, and never say what they imply.
2. **Manager:** quote news exactly, and never say what it implies.
3. **Reviewer:** a "NEWS RULE" that flags any description of a news item that adds meaning the headline does not state (words like "strong", "proactive", "reinforcing").

Test so far: with the new rule the reviewer **failed the spun sentence 2 times out of 2**, naming the "proactive security patches" and "reinforcing its reputation" claims. **Still to do:** check that the reviewer still **passes** an answer that quotes the headlines fairly (so it has not become too strict), and run the full pipeline on the Microsoft question once. We stopped here because of the daily token limit, so this check is pending.

**Lesson:** a reviewer checks whether facts appear in the evidence. It does not automatically check whether you described a fact *fairly*. You have to tell it to look for that, and even then it is a language model, so it can still miss things.

### Exercise

1. Run Step 1 for `AAPL` and `TSLA`. Which headlines did the checker keep? Do you agree with each?
2. In Step 5, add a third planted claim to `bad` (for example, "Apple has no debt."). Does the reviewer catch it?
3. Ask `ask_with_review` about **two** companies. How many times did the manager call `research_company`?
4. Which would you prefer: a reviewer that sometimes flags good answers, or one that sometimes misses bad ones? Why?

---

## Videos and references

*(Add your links here. I will use them to shape the next lessons.)*

- Official docs: https://docs.langchain.com

---

## Questions and notes

*(Your own notes go here.)*
