# mna_automation/app.py

import asyncio

import streamlit as st
from autogen import AssistantAgent, UserProxyAgent

from agents.strategy_agent import STRATEGY_PROMPT
from config.settings import BASE_CONFIG


class TrackableStrategyAgent(AssistantAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="Strategy_Advisor",
            system_message=STRATEGY_PROMPT,
            llm_config=BASE_CONFIG,
            **kwargs,
        )
        self.strategy = {}
        self.strategy_approved = False

    def _process_received_message(self, message, sender, silent):
        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = message

        if content.strip():
            with st.chat_message("Strategy_Advisor"):
                st.markdown(content)
        return super()._process_received_message(message, sender, silent)


class TrackableUserProxyAgent(UserProxyAgent):
    def _process_received_message(self, message, sender, silent):
        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = message

        if content.strip():
            with st.chat_message("User"):
                st.markdown(content)
        return super()._process_received_message(message, sender, silent)

    def get_human_input(self, prompt: str) -> str:
        return st.session_state.current_user_input


def init_agents():
    strategy_agent = TrackableStrategyAgent()
    user_proxy = TrackableUserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        code_execution_config=False,
        max_consecutive_auto_reply=1,
        is_termination_msg=lambda x: x.get("content", "").strip().endswith("TERMINATE"),
    )
    return strategy_agent, user_proxy


def main():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("M&A Automation")

    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.strategy_agent, st.session_state.user_proxy = init_agents()
        st.session_state.chat_initiated = False

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Your response"):

        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.current_user_input = prompt

        with st.spinner("Processing..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def process_chat():
                if not st.session_state.chat_initiated:
                    chat_response = await st.session_state.user_proxy.a_initiate_chat(
                        st.session_state.strategy_agent,
                        message=prompt,
                        max_consecutive_auto_reply=1,
                    )
                    st.session_state.chat_initiated = True
                else:
                    await st.session_state.user_proxy.a_send(
                        prompt,
                        st.session_state.strategy_agent,
                    )

            try:
                loop.run_until_complete(process_chat())
            finally:
                loop.close()

        last_message = (
            st.session_state.messages[-1]["content"]
            if st.session_state.messages
            else ""
        )
        if "TERMINATE" in last_message:
            st.success("✅ Strategy development completed!")

            markdown_start = last_message.find("```markdown")
            if markdown_start != -1:
                markdown_end = last_message.find("```", markdown_start + 10)
                if markdown_end != -1:
                    strategy_content = last_message[
                        markdown_start + 10 : markdown_end
                    ].strip()
                    st.download_button(
                        label="Download Strategy Document",
                        data=strategy_content,
                        file_name="mna_strategy.md",
                        mime="text/markdown",
                    )


if __name__ == "__main__":
    main()
