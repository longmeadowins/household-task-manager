import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Home Manager", page_icon="🏠")

# --- SECURITY SETTINGS ---
# 🔒 CHANGE THIS to your desired password
APP_PASSWORD = "penny3200"

# Check if password is correct via URL or Input
auth_success = False

# 1. Check URL (e.g. ?password=change_me_123)
if st.query_params.get("password") == APP_PASSWORD:
    auth_success = True
else:
    # 2. Check manual input
    password_input = st.text_input("Enter Password to Access", type="password")
    if password_input == APP_PASSWORD:
        auth_success = True

# Stop execution if password is wrong
if not auth_success:
    st.stop()

# ==========================================
#     AUTHENTICATED APP STARTS HERE
# ==========================================

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Helper Functions ---
def get_data():
    try:
        df = conn.read(ttl=0)
        # Handle empty or new sheet structure
        if 'ID' not in df.columns:
            return pd.DataFrame(columns=['ID', 'Task', 'Due Date', 'Recurrence', 'Notes'])
        return df
    except:
        return pd.DataFrame(columns=['ID', 'Task', 'Due Date', 'Recurrence', 'Notes'])

def save_data(df):
    conn.update(data=df)

# --- App Layout ---
st.title("🏠 Household Task Manager")

# --- Sidebar: Add New Task ---
with st.sidebar:
    st.header("Add New Task")
    with st.form("add_task_form", clear_on_submit=True):
        task_name = st.text_input("Task Name")
        due_date = st.date_input("First Due Date", date.today())
        recurrence = st.number_input("Repeats every (days)", min_value=1, value=30)
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("Add Task")
        if submitted and task_name:
            df = get_data()
            
            # Generate new ID
            new_id = 1 if df.empty else df['ID'].max() + 1
            
            # Create new row
            new_task = pd.DataFrame([{
                'ID': new_id, 
                'Task': task_name, 
                'Due Date': str(due_date), 
                'Recurrence': recurrence, 
                'Notes': notes
            }])
            
            # Append and Save
            updated_df = pd.concat([df, new_task], ignore_index=True)
            save_data(updated_df)
            st.success(f"Added: {task_name}")
            st.rerun()

# --- Main Dashboard ---
df = get_data()

if df.empty:
    st.info("No tasks found. Add one in the sidebar!")
else:
    # Ensure dates are datetime objects
    df['Due Date'] = pd.to_datetime(df['Due Date']).dt.date
    today = date.today()
    
    # Sort by date
    df = df.sort_values(by="Due Date")

    tab1, tab2 = st.tabs(["Action Items", "All Tasks"])

    # --- View 1: Cards ---
    with tab1:
        st.caption("Tasks update automatically in your Google Sheet.")
        for index, row in df.iterrows():
            delta = (row['Due Date'] - today).days
            
            if delta < 0:
                status = "🔴 Overdue"
                border = True
            elif delta <= 7:
                status = "🟠 Due Soon"
                border = True
            else:
                status = "🟢 Upcoming"
                border = True

            with st.container(border=border):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.subheader(row['Task'])
                    st.caption(f"{status} • Every {row['Recurrence']} days")
                    if pd.notna(row['Notes']) and row['Notes'] != "":
                        st.text(row['Notes'])
                with c2:
                    st.metric("Due", str(row['Due Date']), delta=f"{delta} days", delta_color="inverse")
                with c3:
                    st.write("")
                    if st.button("✅ Complete", key=f"comp_{row['ID']}"):
                        # Calculate next date
                        next_date = row['Due Date'] + timedelta(days=row['Recurrence'])
                        if next_date < today:
                            next_date = today + timedelta(days=row['Recurrence'])
                        
                        # Update DataFrame
                        df.at[index, 'Due Date'] = str(next_date)
                        save_data(df)
                        st.toast(f"Done! Next due: {next_date}")
                        st.rerun()

    # --- View 2: Table & Delete ---
    with tab2:
        st.dataframe(df, use_container_width=True)
        
        st.subheader("Delete Task")
        task_list = df['Task'].tolist()
        to_delete = st.selectbox("Select task to delete", task_list, index=None)
        
        if to_delete and st.button("🗑️ Delete Task"):
            df = df[df['Task'] != to_delete]
            save_data(df)
            st.success("Deleted!")
            st.rerun()
