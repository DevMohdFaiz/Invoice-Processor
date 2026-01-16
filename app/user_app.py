import streamlit as st
import hashlib
import sqlite3
import os

from src.database import UserDB
import src
import importlib
importlib.reload(src)
user_db= UserDB()
def test_func():
    return "True"
# if st.button("clicks", key="test_btn"):
#     st.write(user_db.add_user("ola", "lo"))


def show_login_page():
    """Display login/signup page."""
    
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
                    st.error("Invalid credentials")
        
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
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                new_user_status = user_db.add_user(new_username, new_password)
                st.write(new_user_status)
                if new_user_status == "failure":
                    st.error(f"**{new_username}** is already taken! Pls try another username")
                elif new_user_status=="success":
                    st.success(f"Congratulations **{new_username}** your account has been successfully created")
            st.success(new_user_status)

            # elif user_db.add_user(new_username, new_password) is None:
            #     st.error(f"**{new_username}** is already taken! Pls try another username")
            # elif user_db.add_user(new_username, new_password) is not None:
            #     st.success(f"Congratulations **{new_username}** your account has been successfully created")
# def get_user_storage():
#     """Get storage for current user."""
    
#     from your_storage_module import ReceiptStorage
    
#     username = st.session_state.get('username', 'demo')
#     is_demo = st.session_state.get('demo_mode', False)
    
#     if is_demo:
#         # Demo data
#         return ReceiptStorage(
#             db_path='receipts.db',
#             vector_db_path='./chroma_receipts'
#         )
#     else:
#         # User-specific data
#         user_dir = f"users/{username}"
#         return ReceiptStorage(
#             db_path=f'{user_dir}/receipts.db',
#             vector_db_path=f'{user_dir}/chroma'
#         )


# ============================================
# MAIN APP
# ============================================

# Initialize
# setup_user_db()

# Check authentication
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    show_login_page()
else:
    # Sidebar
    with st.sidebar:
        st.markdown(f"**User:** {st.session_state.username}")
        
        if st.session_state.get('demo_mode', False):
            st.caption("Demo Mode (Read-only)")
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.demo_mode = False
            st.rerun()
    
    # Get user's storage
    # storage = get_user_storage()
    
    # Your app pages here
    # ... rest of your app ...
