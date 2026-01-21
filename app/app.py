import os
import streamlit as st
import pandas as pd
from datetime import datetime

from src import rag_system
rag_ai_chat = rag_system.AIChat()

# Page config
st.set_page_config(
    page_title="Invoice Processor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .stat-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .receipt-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }
    # .stChatMessage {
    #     background-color: #f8f9fa;
    #     border-radius: 0.5rem;
    #     padding: 1rem;
    #     margin-bottom: 0.5rem;
    # }
</style>
""", unsafe_allow_html=True)


if 'messages' not in st.session_state:
    st.session_state.messages = {'user_messages': [], 'ai_messages': []}
if 'receipts_processed' not in st.session_state:
    st.session_state.receipts_processed = 0


with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio(
        "Select Page",
        ["Upload Receipt", "View Receipts", "Analytics", "Chat Assistant"],
        # label_visibility="collapsed"
    )
    
    st.markdown("---")

# col1, col2 = st.columns(2)
tab1, tab2 = st.tabs(["AI", "Other"])
with tab1:
    st.subheader("AI Chat")

    # Display all previous messages
    for idx in range(len(st.session_state.messages['user_messages'])):
        with st.chat_message('user'):
            st.write(st.session_state.messages['user_messages'][idx])
        with st.chat_message('assistant'):
            st.write(st.session_state.messages['ai_messages'][idx])
    
 
    user_message = st.chat_input("Ask me anything about your receipts...")
    if user_message:
        with st.chat_message('user'):
            st.write(user_message)

        with st.chat_message('assistant'):
            with st.spinner("Thinking..."):
                ai_response = rag_ai_chat.ai_chat(user_message)
                if ai_response:
                    st.write(ai_response[1])

                    # Save messages to session state
                    st.session_state.messages['user_messages'].append(user_message)
                    st.session_state.messages['ai_messages'].append(ai_response[1])
                else:
                    error_msg = "Sorry, I encountered an error. Please try again."
                    st.write(error_msg)
                    st.session_state.messages['user_messages'].append(user_message)
                    st.session_state.messages['ai_messages'].append(error_msg)
        
        st.rerun()


