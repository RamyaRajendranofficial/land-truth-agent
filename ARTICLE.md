# Land Truth Agent: checking a land broker's word before a villager pays

## The problem

In villages around Coimbatore, Tamil Nadu, buying a piece of land often starts with a broker's description. "This area gets good rain." "Water is always available here." "The rate is 4 lakh per cent, that's the market price." For a family putting their savings into a plot, these three claims decide everything: whether crops will survive, whether a borewell will find water, and whether they are paying a fair price.

The trouble is that a buyer has no easy way to check any of it. Rainfall records sit in technical portals. Groundwater status lives in government reports written for engineers. The official guideline value is on a registration website most people never open. So the broker's word becomes the only "data" in the room, and a dry area gets sold as a green one at an inflated price.

Land Truth Agent is a chatbot that puts independent data back on the buyer's side, in their own language.

## Who it helps

Rural land buyers and smallholder farmers, the people who carry the most risk when a land claim turns out to be false and who are least served by existing tools. It speaks Tamil, uses plain words, and is reachable through a simple chat window instead of a government portal.

## What it does

You tell it what the broker said. For example: *"A broker says Annur has good rain and water, and wants Rs 4,00,000 per cent. Is that true?"*

The agent then:

1. **Checks the rain claim** against real rainfall history for that location, year by year, including monsoon totals and dry spells.
2. **Checks the water claim** against groundwater status (safe, semi-critical, critical, or over-exploited).
3. **Checks the price** by comparing the quoted rate against the government guideline value.
4. **Gives a clear verdict on each claim**: SUPPORTED, NOT SUPPORTED, or NOT ENOUGH DATA. It never calls a place "good" without data behind it.
5. **Ends with an action list**: the questions to ask the broker and the documents to demand (patta, chitta, encumbrance certificate, recent sale deeds of nearby plots, proof of a water source).

Every answer can come back in Tamil, so the person making the decision reads it in the language they think in.

## How it's built

Land Truth Agent is built with the **Strands Agents SDK** as a small multi-agent system:

- A **coordinator agent** reads the buyer's message, decides which claims need checking, and assembles the final verdict.
- A **water analyst** sub-agent handles rainfall and groundwater.
- A **price analyst** sub-agent handles the guideline-value comparison.

The coordinator calls the specialists as tools and passes each one a language rule, so a Tamil request produces a fully Tamil report end to end. The agent's tools are plain Python functions: live rainfall from the free Open-Meteo historical API, and groundwater and guideline values from a local dataset that is clearly marked as verified or placeholder. Conversation memory persists between sessions, so a buyer can come back and compare a second plot.

The behavior rules live in the system prompt as guardrails: never invent a number, always disclose when a figure is unverified, state once that rainfall is a model estimate rather than a plot-level gauge reading, and always advise a registered surveyor and a legal title check before any advance is paid.

It runs two ways: a terminal chat for developers and a one-page web chatbot (Streamlit) for everyone else.

## What I learned

The hardest part was not the code, it was deciding what the agent is *not* allowed to say. An agent that confidently declares land "good" is worse than no agent, because it launders a guess into something that looks official. So the most important design choices were the honest ones: label every claim's evidence level, show uncertainty, mark placeholder data as placeholder, and refuse to produce a market price when no authoritative source exists. Building the guardrails taught me more about trustworthy agents than building the tools did.

## Honest limitations

- Rainfall comes from a gridded climate model (ERA5), not a rain gauge on the exact plot, so it is an indicator, not a measurement.
- There is no single authoritative "market price" source. The agent can only compare to the government guideline value and flag outliers.
- It is not legal or valuation advice. It always points the user to a registered surveyor and a property lawyer before any money changes hands.

## Try it

Source code: https://github.com/RamyaRajendranofficial/land-truth-agent

```
pip install -r requirements.txt
streamlit run app.py
```

Then ask it about a plot a broker is selling you, and read the verdict before you believe the pitch.
