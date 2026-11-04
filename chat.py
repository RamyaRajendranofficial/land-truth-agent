"""Land Truth Agent: check a broker's land claims against real data.

    python chat.py                      # default session
    python chat.py --session-id ramya   # resume a named session
    python chat.py --lang ta            # always reply in Tamil
    python chat.py --lang en            # always reply in English
    python chat.py                      # auto: Tamil if you type Tamil script

On Windows PowerShell, run this once per terminal session first so emoji and
the rupee sign display correctly:
    chcp 65001

Set MODEL_ID to use another Bedrock model, e.g. amazon.nova-pro-v1:0
(PowerShell:  $env:MODEL_ID = "amazon.nova-pro-v1:0").
"""

import argparse
import os
import sys

# Windows PowerShell's default console codepage (cp1252) can't print some
# Unicode characters the model generates (em-dashes, Tamil script, etc.).
# Force UTF-8 stdout so those don't crash the chat loop.
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

from strands import Agent, tool
from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry
from strands.models import BedrockModel
from strands.session.file_session_manager import FileSessionManager

from land_tools import (
    check_quoted_price,
    get_groundwater_status,
    get_guideline_value,
    get_rainfall_history,
)


def make_model():
    """Default model unless MODEL_ID is set (useful for Nova / sponsored credits)."""
    model_id = os.getenv("MODEL_ID")
    return BedrockModel(model_id=model_id) if model_id else None


def build_agent(**kwargs) -> Agent:
    model = make_model()
    if model:
        kwargs["model"] = model
    return Agent(**kwargs)


_TAMIL_RANGE = range(0x0B80, 0x0BFF + 1)


def contains_tamil(text: str) -> bool:
    """True if the text has Tamil script characters."""
    return any(ord(ch) in _TAMIL_RANGE for ch in text)


def language_instruction(lang: str, user_input: str) -> str:
    """Build the language rule to prepend for this turn.

    lang: "ta" forces Tamil, "en" forces English, "auto" follows the
    script of the user's message (defaults to English if no Tamil detected).
    """
    if lang == "ta" or (lang == "auto" and contains_tamil(user_input)):
        return (
            "LANGUAGE RULE: Reply ONLY in Tamil (தமிழ்), in simple everyday words a "
            "villager would understand. Keep numbers in digits (e.g. Rs, mm, cent)."
        )
    if lang == "en":
        return "LANGUAGE RULE: Reply in simple English."
    return "LANGUAGE RULE: Reply in the same language the user wrote in."


# ---- Specialist agents, exposed to the coordinator as tools ----------------

WATER_PROMPT = """You are a water analyst for rural land buyers in Tamil Nadu.
Use get_rainfall_history and get_groundwater_status. Report facts with numbers.
Say clearly when data is missing or marked as a placeholder. Never guess."""

PRICE_PROMPT = """You are a land price analyst for rural land buyers in Tamil Nadu.
Use get_guideline_value and check_quoted_price. Report facts with numbers.
Say clearly when data is missing or marked as a placeholder. Never guess a
market price: you can only compare against the government guideline value."""


@tool
def water_analyst(question: str) -> str:
    """Ask the water analyst about rainfall and groundwater at a village.

    Args:
        question: A question that includes the village name, e.g.
            'Is Annur dry? Check rainfall and groundwater.' Include any
            LANGUAGE RULE line from the coordinator so the answer matches.
    """
    agent = build_agent(
        tools=[get_rainfall_history, get_groundwater_status],
        system_prompt=WATER_PROMPT,
        callback_handler=None,
    )
    return str(agent(question))


@tool
def price_analyst(question: str) -> str:
    """Ask the price analyst to compare a quoted price with the guideline value.

    Args:
        question: A question that includes the village and the quoted price per
            cent. Include any LANGUAGE RULE line from the coordinator so the
            answer matches.
    """
    agent = build_agent(
        tools=[get_guideline_value, check_quoted_price],
        system_prompt=PRICE_PROMPT,
        callback_handler=None,
    )
    return str(agent(question))


# ---- Hook: show which specialist is being consulted ------------------------

class ShowToolCalls(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.show)

    def show(self, event: BeforeToolCallEvent) -> None:
        print(f"\n[checking] {event.tool_use['name']}")


# ---- Coordinator with firm rules (steering via system prompt) --------------

SYSTEM_PROMPT = """You are Land Truth, a friendly assistant that helps villagers in
Tamil Nadu (India) check what a land broker told them before they buy.

How to work:
1. Find the village and the broker's claims (e.g. 'good rain', 'water available',
   price per cent). Ask briefly if the village name or price is missing.
2. Call water_analyst for water claims and price_analyst for price claims.
3. Compare each claim with the data. Say clearly: CLAIM SUPPORTED, NOT SUPPORTED,
   or NOT ENOUGH DATA.
4. Finish with a short list of questions to ask the broker and documents to
   ask for (patta, chitta, EC, sale deeds of nearby plots, water source proof).

Hard rules:
- Never call a place good or bad without data from the analysts.
- Never invent prices, rainfall or groundwater numbers.
- If a figure is marked placeholder or unverified, tell the user so.
- Rainfall is model-based, not from a gauge at the plot. Say so once.
- You are not a lawyer or valuer. Always advise a registered surveyor and a
  legal check of title before paying any advance.
- Use simple words.
- Each user message may start with a LANGUAGE RULE line. Follow it for your
  final answer, and copy that same rule line into every question you send to
  water_analyst or price_analyst so their findings come back in that language.
- When answering in Tamil, keep proper nouns (village names, patta, chitta, EC,
  CGWB) recognisable, and keep numbers in digits."""


def main():
    parser = argparse.ArgumentParser(description="Land Truth Agent")
    parser.add_argument("--session-id", default="land-session-001")
    parser.add_argument(
        "--lang",
        choices=["auto", "ta", "en"],
        default="auto",
        help="Reply language: ta = always Tamil, en = always English, "
        "auto = Tamil if you type Tamil script (default).",
    )
    args = parser.parse_args()

    agent = build_agent(
        tools=[water_analyst, price_analyst],
        hooks=[ShowToolCalls()],
        system_prompt=SYSTEM_PROMPT,
        session_manager=FileSessionManager(
            session_id=args.session_id, storage_dir="./sessions"
        ),
    )

    restored = len(agent.messages)
    print(f"Land Truth Agent (session: {args.session_id}) - type 'quit' to exit.")
    if restored:
        print(f"Restored {restored} message(s) from a previous session.")
    print('Try: "A broker says Annur has good rain and water, and wants Rs 400000 per cent. Is that true?"\n')

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! Your conversation is saved.")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye! Your conversation is saved.")
            break
        if not user_input:
            continue
        print("\nAgent: ", end="")
        rule = language_instruction(args.lang, user_input)
        agent(f"{rule}\n\n{user_input}")
        print()


if __name__ == "__main__":
    main()
