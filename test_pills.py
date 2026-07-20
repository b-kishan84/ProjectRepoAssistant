import streamlit as st
selection = st.pills("Quick Actions", ["Explain", "Refactor"])
st.write("Selected:", selection)
