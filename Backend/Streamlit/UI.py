import streamlit as st
import fastapi


st.title("DB Viewer X Editor(Cache Version)")
st.header("_Streamlit_ is :blue[cool] :sunglasses:")
st.markdown("Upload a PDF file containing test cases in JSON-like blocks. The parser will extract the test cases, classify them, and save them to the database.")

import requests

API_BASE_URL = "http://localhost:8000"
if "session_items" not in st.session_state:
    st.session_state.session_items = []

st.subheader("Upload PDF")
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if st.button("Upload and Process"):
    if uploaded_file is not None:
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        try:
            response = requests.post(f"{API_BASE_URL}/items/upload-pdf", files=files)
            if response.status_code == 200:
                new_items = response.json()
                st.session_state.session_items = new_items
                st.success(f"PDF processed successfully! Extracted {len(new_items)} cases.")
                st.rerun()
            else:
                st.error(f"Upload failed: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the FastAPI server. Ensure it is running.")
    else:
        st.warning("Please select a file.")

st.divider()

st.subheader("Retrieve Item")
item_id = st.text_input("Enter Item ID")

if st.button("Fetch Item"):
    if item_id:
        try:
            item_id = item_id.strip().replace('"', '')
            response = requests.get(f"{API_BASE_URL}/items/{item_id}")
            
            if response.status_code == 200:
                st.write("Item Details:")
                st.json(response.json())
            else:
                st.error(f"Item not found: {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the FastAPI server.")
    else:
        st.warning("Please enter an ID.")

st.divider()


st.subheader("Data Editor")
st.write("Edit 'Expected Result' and 'Steps' for the items uploaded above.")
import pandas as pd
items = st.session_state.session_items
if items:
    df = pd.DataFrame(items)
    
    # Reorder or select columns for display if needed
    # We want to make only 'expected_result' and 'steps' editable
    
    # 'steps' is a list, let's join it for easier editing if it's a list
    df['steps'] = df['steps'].apply(lambda x: "\n".join(x) if isinstance(x, list) else str(x))
    
    edited_df = st.data_editor(
        df,
        column_config={
            "id": st.column_config.TextColumn("MongoDB ID", disabled=True),
            "item_id": st.column_config.NumberColumn("Case ID", disabled=True),
            "expected_result": st.column_config.TextColumn("Expected Result", disabled=False),
            "steps": st.column_config.TextColumn("Steps", disabled=False),
            # Hide everything else
            "title": None,
            "type": None,
            "description": None,
            "image_id": None,
            "created_at": None,
            "processing_status": None,
            "task_id": None,
            "metadata": None
        },
        use_container_width=True,
        hide_index=True,
        key="items_editor"
    )

    if st.button("Save Changes"):
        # Detect changes
        # st.data_editor returns the full edited dataframe. We compare with original.
        # However, for simplicity here, we can just iterate and update everything that changed.
        # Or more efficiently, use st.session_state.items_editor['edited_rows']
        
        changes = st.session_state.get("items_editor", {}).get("edited_rows", {})
        if not changes:
            st.info("No changes to save.")
        else:
            success_count = 0
            for index, updates in changes.items():
                idx = int(index)
                item_id = df.iloc[idx]['id']
                
                # If steps was edited, convert it back to a list
                if 'steps' in updates:
                    updates['steps'] = [s.strip() for s in updates['steps'].split("\n") if s.strip()]
                
                try:
                    res = requests.patch(f"{API_BASE_URL}/items/{item_id}", json=updates)
                    if res.status_code == 200:
                        success_count += 1
                        # Update the local session state so the change persists on rerun
                        for field, value in updates.items():
                            st.session_state.session_items[idx][field] = value
                    else:
                        st.error(f"Failed to update item {item_id}: {res.text}")
                except Exception as e:
                    st.error(f"Error updating item {item_id}: {e}")
            
            if success_count > 0:
                st.success(f"Successfully updated {success_count} item(s)!")
                # No st.rerun() needed if we updated session_state correctly, 
                # but a rerun helps refresh the data_editor state.
                st.rerun()
else:
    st.info("No items found in the database. Upload a PDF to get started.")