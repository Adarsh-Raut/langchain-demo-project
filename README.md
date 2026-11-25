# LangChain Learning Project: Stock Advisor Agent

A hands-on project for learning LangChain by building a **stock research agent**. You tell the agent a budget and a company name. It looks up real market data, explains what it found, and (in later lessons) asks for your approval before any "buy" action.

You learn by running small notebooks one cell at a time, then combining the pieces into a working terminal app.

> **This is a learning project, not financial advice.** The agent's answers are research output from a language model. Do not make real investment decisions from it.

---

## What you will build

A user says: *"I have $5,000 and I prefer low risk. I'm thinking about Apple."*

The agent then:

1. Finds the stock ticker from the company name (Apple becomes `AAPL`).
2. Fetches the price, valuation numbers, price trend and recent news.
3. Compares the stock against the overall market (S&P 500).
4. Remembers your budget and risk level for the rest of the conversation.
5. Explains the trend and the evidence in plain language.
6. Pauses and asks you to approve, edit or reject before "buying" (a simulated order, no real money).

Everything runs in the terminal and in notebooks. There is no website, no database and no real broker. Market data comes from the free `yfinance` library.

---

## Project status

| # | Lesson | Notebook | Status |
|---|--------|----------|--------|
| 1 | Models, messages, tools, first agent | `notebooks/01_basics.ipynb` | Done |
| 2 | Tools with real stock data | `notebooks/02_tools.ipynb` | Done |
| 3 | Memory across messages | `notebooks/03_memory.ipynb` | Done |
| 4 | Human-in-the-loop approval | `notebooks/04_human_in_the_loop.ipynb` | Done |
| 5 | Sub-agents: news checker, researcher, reviewer | `notebooks/05_sub_agents.ipynb` | Done |
| 6 | Context: files and user details | | Planned |
| 7 | Final terminal app | `stock_advisor/` | Planned |

The full written lessons are in [`langchain.md`](langchain.md). Read a lesson there, then run the matching notebook.

---

## Setup

### What you need

- **Python 3.10 or newer.** Check with `python3 --version`.
- **A free Groq API key.** Create one at https://console.groq.com/keys.
- **VS Code** with the *Python* and *Jupyter* extensions (recommended), or JupyterLab.
- Internet access, because the model and the market data are online.

The steps below were tested on Linux (WSL Ubuntu). macOS works the same way. On Windows, use WSL.

### 1. Get the code

```bash
git clone https://github.com/Adarsh-Raut/langchain-demo-project.git
cd langchain-demo-project
```

### 2. Create the virtual environment and install packages

A virtual environment is a private copy of Python for this project, so its packages do not mix with the rest of your computer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run `source .venv/bin/activate` again each time you open a new terminal.

### 3. Add your API key

```bash
cp .env.example .env
```

Open `.env` (not `.env.example`) and replace `paste-your-key-here` with your real key, with no quotes and no spaces:

```
GROQ_API_KEY=gsk_your_real_key
```

`.env` is listed in `.gitignore`, so your key is never uploaded to GitHub. Never put your key in `.env.example` or in any notebook.

### 4. Register the notebook kernel

This lets VS Code and JupyterLab find your environment:

```bash
python -m ipykernel install --user --name langchain-learn --display-name "LangChain Learn"
```

---

## How to use the notebooks

### In VS Code

1. Open the folder in VS Code.
2. Open a notebook from `notebooks/`.
3. Click **Select Kernel** at the top right, choose **Python Environments**, then pick `.venv`. The **LangChain Learn** kernel also works.
4. Click into a cell and press **Shift+Enter** to run it and move to the next one.

### In JupyterLab

```bash
jupyter lab
```

Then open a notebook and choose the **LangChain Learn** kernel.

### Tips

- Run cells **from top to bottom**. Later cells depend on earlier ones.
- If something behaves oddly, click **Restart** at the top of the notebook and run again from the first cell.
- Each notebook ends with an exercise. Do it before moving on.
- Long answers can be cut off with "Output is truncated". Click **scrollable element** under the output to read all of it.

---

## Project structure

```
langchain-demo-project/
├── README.md              This file
├── langchain.md           The written lessons (read these alongside the notebooks)
├── requirements.txt       Python packages, with exact versions
├── .env.example           Template for your API key
├── .env                   Your real key (you create it; it is never uploaded)
├── notebooks/
│   ├── 01_basics.ipynb    Models, messages, tools, first agent
│   ├── 02_tools.ipynb     Real stock tools and the tool chain
│   ├── 03_memory.ipynb    Memory with a checkpointer and thread ids
│   ├── 04_human_in_the_loop.ipynb   Approve, edit or reject an order
│   └── 05_sub_agents.ipynb          News checker, researcher and reviewer sub-agents
└── stock_advisor/
    ├── __init__.py
    ├── tools.py           The stock tools, shared by every notebook
    └── agents.py          The sub-agents (news checker, researcher, reviewer)
```

### The sub-agents (`stock_advisor/agents.py`)

| Sub-agent | What it does |
|-----------|--------------|
| News checker | Keeps only headlines that are really about the company. Used by `get_relevant_news` |
| Researcher | Runs all the research tools and reports facts only. The main advisor calls it as `research_company` |
| Reviewer | Checks an answer against the raw tool results and lists unsupported claims |

### The stock tools (`stock_advisor/tools.py`)

| Tool | What it does |
|------|--------------|
| `search_ticker` | Turns a company name like "Apple" into a ticker like `AAPL` |
| `get_snapshot` | Current price, P/E ratios, market cap, sector, 52-week range |
| `get_price_trend` | Price change, high and low over a period (1mo to 5y) |
| `get_market_trend` | The same for the S&P 500, so a stock can be compared with the market |
| `get_recent_news` | The latest headlines for a ticker |
| `calculate_shares` | Exact share count and leftover cash. The agent must use this instead of doing math itself |
| `buy_stock` | A **simulated** order that only writes to a list. Always behind a human approval step |

---

## Key ideas you will learn

| Idea | In one sentence |
|------|-----------------|
| **Model** | The language model. It can only produce text. |
| **Tool** | A normal Python function the model may ask for. Your code runs it. |
| **Agent** | A loop: the model thinks, asks for a tool, reads the result, and repeats until it can answer. |
| **Memory** | A checkpointer saves the conversation so the agent remembers earlier messages. A thread id names each conversation. |
| **Human-in-the-loop** | The agent pauses before a risky action and waits for a person to approve, edit or reject it. |
| **Sub-agent** | A second agent that does one focused job for the main agent. You wrap it in a tool so the main agent can call it. |
| **Structured output** | Forcing an agent to answer in a fixed shape (for example a list of numbers and a reason) so your code can read it safely. |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Key found: False` | Your key is not in `.env`. Check that the file is named `.env`, the line is `GROQ_API_KEY=...`, and you saved it. |
| `model_not_found` / "does not exist or you do not have access" | Groq changes its model list. Run Step 7 in `02_tools.ipynb` to list the models your key can use, then change the `MODEL` value. Pick one that supports tools. |
| `ModuleNotFoundError` | The wrong kernel is selected. Choose `.venv` at the top right of the notebook. |
| `No module named 'stock_advisor'` | Run the notebook from the `notebooks/` folder. The notebooks add the parent folder to the path themselves. |
| `429 rate_limit_exceeded` from Groq | The free tier allows about 8,000 tokens per minute and the sub-agents use many. The code retries automatically. If it still fails, wait a minute and rerun the cell |
| Stock data is empty or errors | `yfinance` is an unofficial source and can be rate-limited. Wait a minute and try again. |
| Notebook shows a dot (unsaved) after a file changed on disk | Close the tab, choose **Don't Save**, then reopen it. Saving an out-of-date copy would overwrite the newer file. |

---

## Known limitations

- **The agent can state things no tool gave it.** Language models sometimes fill gaps from memory (for example a dividend yield or an "average P/E"). The system prompts ask for tool-only numbers and a reviewer sub-agent checks answers, which reduces this but does not remove it.
- **News is checked, not perfect.** A sub-agent now removes off-topic headlines, but it is a language model and sometimes keeps a borderline one.
- **The reviewer is a model too.** It catches most made-up claims but can miss mild embellishments.
- **Edits are not checked.** If you edit an order to more shares than your budget, it still goes through. Budget checks are an exercise in Lesson 4.
- **Memory is temporary.** `InMemorySaver` is lost when the notebook restarts.
- **Data is unofficial.** `yfinance` is fine for learning, not for production.

---

## Tech used

- [LangChain](https://docs.langchain.com) 1.x for agents, tools and sub-agents
- [LangGraph](https://langchain-ai.github.io/langgraph/) for memory and human-in-the-loop
- [Groq](https://groq.com) for the language model (`openai/gpt-oss-120b`)
- [yfinance](https://github.com/ranaroussi/yfinance) for market data
- Jupyter notebooks for running one cell at a time
