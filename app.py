"""Land Truth Agent - web chatbot (Streamlit).

Run:
    streamlit run app.py

This wraps the same coordinator agent used by chat.py in a simple browser
chat window, so anyone can use it without a terminal.
"""

import streamlit as st
from strands import Agent, tool
from strands.session.file_session_manager import FileSessionManager

from chat import (
    PRICE_PROMPT,
    SYSTEM_PROMPT,
    WATER_PROMPT,
    build_agent,
    language_instruction,
)
from land_tools import (
    check_quoted_price,
    get_groundwater_status,
    get_guideline_value,
    get_rainfall_history,
)

st.set_page_config(page_title="Land Truth Agent", page_icon="🌾")


@st.cache_resource(show_spinner=False)
def get_agent(session_id: str) -> Agent:
    """One persistent agent per browser session id (cached across reruns)."""

    @tool
    def water_analyst(question: str) -> str:
        """Ask the water analyst about rainfall and groundwater at a village.

        Args:
            question: A question that includes the village name. Include any
                LANGUAGE RULE line from the coordinator so the answer matches.
        """
        sub = build_agent(
            tools=[get_rainfall_history, get_groundwater_status],
            system_prompt=WATER_PROMPT,
            callback_handler=None,
        )
        return str(sub(question))

    @tool
    def price_analyst(question: str) -> str:
        """Ask the price analyst to compare a quoted price with the guideline value.

        Args:
            question: A question with the village and quoted price per cent.
                Include any LANGUAGE RULE line from the coordinator.
        """
        sub = build_agent(
            tools=[get_guideline_value, check_quoted_price],
            system_prompt=PRICE_PROMPT,
            callback_handler=None,
        )
        return str(sub(question))

    return build_agent(
        tools=[water_analyst, price_analyst],
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
        session_manager=FileSessionManager(
            session_id=session_id, storage_dir="./sessions"
        ),
    )


st.title("🌾 Land Truth Agent")
st.caption(
    "Check a broker's land claims (rain, water, price) against real data, "
    "before you buy. Not legal or valuation advice."
)

with st.sidebar:
    st.header("Settings")
    session_id = st.text_input("Session ID", value="web-user-1")
    lang = st.selectbox(
        "Reply language",
        options=["auto", "ta", "en"],
        format_func=lambda v: {
            "auto": "Auto (match my message)",
            "ta": "Always Tamil",
            "en": "Always English",
        }[v],
    )
    st.divider()
    st.markdown(
        "**Data sources**\n"
        "- Rainfall: Open-Meteo (live)\n"
        "- Groundwater & price: local dataset "
        "(placeholder until verified — see `data/README.md`)"
    )
    if st.button("Clear chat on screen"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input(
    "e.g. A broker says Annur has good rain and water, and wants Rs 400000 per cent. Is that true?"
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        answer_box = st.empty()
        agent = get_agent(session_id)

        rule = language_instruction(lang, prompt)
        with st.spinner("Checking rainfall, groundwater and price data..."):
            result = agent(f"{rule}\n\n{prompt}")
        answer = str(result)
        answer_box.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
