import streamlit as st
from prompts import strategy_prompt_2, dummy_client_prompt
from configs import OAI_CONFIG
from autogen import ConversableAgent


class TrackableConversableAgent(ConversableAgent):

    def _process_received_message(self, message, sender, silent):
        if sender.name == "pm":
            with st.chat_message(sender.name):
                st.markdown(message)
        elif sender.name == "human_proxy":
            with st.chat_message(sender.name):
                st.markdown(message.split("\n")[-1])
        return super()._process_received_message(message, sender, silent)


# Initialize the agents
pm = TrackableConversableAgent(
    "pm",
    system_message=strategy_prompt_2,
    llm_config=OAI_CONFIG,
    code_execution_config=False,
    function_map=None,
    human_input_mode="NEVER",
)

human_proxy = TrackableConversableAgent(
    "human_proxy",
    llm_config=False,
    human_input_mode="ALWAYS",
)

# Streamlit UI
st.title("Conversable Agent Interface")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("Enter your message:")

if user_input:
    # Append user input to chat history
    st.session_state.chat_history.append(f"User: {user_input}")
    # Concatenate chat history into a single string
    chat_context = "\n".join(st.session_state.chat_history)

    # Pass the chat context to the agent and get the response
    response = human_proxy.initiate_chat(pm, message=chat_context)

    # Append agent response to chat history
    st.session_state.chat_history.append(f"SM: {response}")
