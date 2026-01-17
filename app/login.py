import streamlit as st
import hashlib
import sqlite3
import os


@st.cache_data(show_spinner="Initializing user db...")
def load_user_db():
    from src.database import UserDB
    user_db = UserDB()
    return user_db

@st.cache_resource(show_spinner="Initializing receipt db...")
def load_receipt_db():
    from src.database import ReceiptDB
    receipt_db =ReceiptDB()
    return receipt_db


def show_login_page():
    """Display login/signup page."""
    user_db = load_user_db()
    st.markdown("### Receipt Processor")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.markdown("#### Login")
        
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                if user_db.verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid login details!")
        
        with col2:
            if st.button("Demo Mode", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.username = "demo"
                st.session_state.demo_mode = True
                st.rerun()
    
    with tab2:
        st.markdown("#### Create Account")
        
        new_username = st.text_input("Username", key="signup_username")
        new_password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
        
        if st.button("Sign Up", type="primary", use_container_width=True):
            if new_password != confirm_password:
                st.error("Passwords don't match")
            elif len(new_password) < 4:
                st.error("Password must be at least 4 characters")
            else:
                new_user_status = user_db.add_user(new_username, new_password)
                if new_user_status == "failure":
                    st.error(f"**{new_username}** is already taken! Pls try another username.")
                elif new_user_status == "success":
                    st.success(f"Congratulations **{new_username}**, your account has been successfully created")
                # st.rerun()

def get_user_storage():
    """Get storage for current user."""
    receipt_db = load_receipt_db()
    
    username = st.session_state.get('username', 'demo')
    is_demo = st.session_state.get('demo_mode', False)
    
    if is_demo:
        return receipt_db.view_sql_db()
    
#     else:
#         # User-specific data
#         user_dir = f"users/{username}"
#         return ReceiptStorage(
#             db_path=f'{user_dir}/receipts.db',
#             vector_db_path=f'{user_dir}/chroma'
#         )


# setup_user_db()

# Check authentication
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    show_login_page()
else:
    with st.sidebar:
        st.markdown(f"**User:** {st.session_state.username}")
        
        if st.session_state.get('demo_mode', False):
            st.caption("Demo Mode (Read-only)")
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.demo_mode = False
            st.rerun()
    
    storage = get_user_storage()

    st.text(storage)
