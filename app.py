# mna_automation/app.py

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional, Union

import streamlit as st
from autogen import ConversableAgent

from agents.strategy_agent import StrategyAgent
from config.settings import BASE_CONFIG

INITIAL_GREETING = "Hello! I'm your M&A Strategy Advisor. Let's begin crafting a robust acquisition strategy for your company. To start, can you tell me about your company and its current market position?"


class StreamingStrategyAgent(StrategyAgent):
    async def a_get_response(
        self, messages: list, sender: Optional[ConversableAgent] = None
    ) -> AsyncGenerator[str, None]:
        """Stream the response with added error handling"""
        try:
            response = await self.a_generate_reply(messages=messages, sender=sender)
            if response is None:
                return

            content = (
                response.get("content", "")
                if isinstance(response, dict)
                else str(response)
            )
            if not content:
                return

            yield content
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."


class MnAUserProxyAgent(ConversableAgent):
    def get_human_input(self, prompt: str) -> str:
        return st.session_state.current_user_input


def init_agents() -> tuple[StreamingStrategyAgent, MnAUserProxyAgent]:
    """Initialize the agents with error handling"""
    try:
        strategy_agent = StreamingStrategyAgent(
            name="Strategy_Advisor",
            llm_config=BASE_CONFIG,
        )

        user_proxy = MnAUserProxyAgent(
            name="User",
            human_input_mode="TERMINATE",
            code_execution_config=False,
            max_consecutive_auto_reply=0,
            is_termination_msg=lambda x: x.get("content", "")
            .strip()
            .endswith("TERMINATE"),
        )

        return strategy_agent, user_proxy
    except Exception as e:
        st.error(f"Failed to initialize agents: {str(e)}")
        st.stop()


def initialize_session_state() -> None:
    """Initialize the session state with proper typing"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.strategy_agent, st.session_state.user_proxy = init_agents()
        st.session_state.chat_initiated = False
        st.session_state.chat_terminated = False
        st.session_state.messages.append(
            {"role": "assistant", "content": INITIAL_GREETING}
        )

    if "conversation_messages" not in st.session_state:
        st.session_state.conversation_messages = []


def display_chat_history() -> None:
    """Display chat history with markdown rendering"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


async def process_agent_response(content: str) -> str:
    """Process agent response with proper error handling"""
    try:
        st.session_state.conversation_messages.append(
            {"role": "user", "content": content}
        )

        response_placeholder = st.empty()
        accumulated_response = ""

        async for token in st.session_state.strategy_agent.a_get_response(
            messages=st.session_state.conversation_messages,
            sender=st.session_state.user_proxy,
        ):
            accumulated_response += token
            response_placeholder.markdown(accumulated_response + "▌")

        st.session_state.conversation_messages.append(
            {"role": "assistant", "content": accumulated_response}
        )

        response_placeholder.markdown(accumulated_response)

        if "TERMINATE" in accumulated_response:
            st.session_state.chat_terminated = True

        return accumulated_response
    except Exception as e:
        st.error(f"Error processing response: {str(e)}")
        return "I apologize, but I encountered an error. Please try again."


def main() -> None:
    """Main application with improved error handling and UX"""
    st.title("M&A Strategy Advisor")

    initialize_session_state()
    display_chat_history()

    if not st.session_state.chat_terminated:
        if prompt := st.chat_input("Your response"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            st.session_state.current_user_input = prompt

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = loop.run_until_complete(
                            process_agent_response(prompt)
                        )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response}
                        )

                        if "TERMINATE" in response:
                            st.success("✅ Strategy development completed!")
                            st.info(
                                "The strategy has been saved to outputs/strategy.md"
                            )
                    finally:
                        loop.close()
    else:
        st.info("Strategy development has been completed. The chat is now closed.")


if __name__ == "__main__":
    main()
