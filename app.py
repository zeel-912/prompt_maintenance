import streamlit as st
from pymongo import MongoClient
from datetime import date
from streamlit import markdown as st_markdown

st.set_page_config(layout="wide")

# ---- MongoDB Connection ----
client = MongoClient("mongodb://localhost:27017/")
db = client["prompt_maintenance"]
prompt_collection = db["prompts"]

# ---- Helper for Status Emoji ----
def get_status_emoji(status):
    return {"Approved": "🟢", "Draft": "🟡", "Deprecated": "🔴"}.get(status, "🟡")

# ---- Fetch All Prompts ----
def get_all_prompts():
    return list(prompt_collection.find({}, {"_id": 1, "title": 1, "status": 1, "prompt_id": 1}))
# Improved: sort by status (Approved > Draft > Deprecated), then title
status_order = {"Approved": 0, "Draft": 1, "Deprecated": 2}
all_prompts = get_all_prompts()

all_prompts_sorted = sorted(
    all_prompts,
    key=lambda p: (status_order.get(p.get("status", "Draft"), 1), p.get("title", ""))
)

def sidebar_prompt_display(p):
    line = f"{get_status_emoji(p.get('status', 'Draft'))} **{p.get('title', 'Untitled')}**"
    model = p.get('model', '')
    pid = p.get('prompt_id', str(p['_id'])[:6])
    tags = ", ".join(p.get('tags', []))
    status = p.get('status', '')
    # Display all info as markdown, with model and tags as subtitle
    subtitle = f"<span style='font-size: 11px; color: #ccc;'>[{pid}] • {model} • {status} • {tags}</span>"
    return f"{line}<br>{subtitle}"

sidebar_options = ["➕ New Prompt"] + [
    f"{get_status_emoji(p.get('status', 'Draft'))} {p.get('title', 'Untitled')} [{p.get('prompt_id', str(p['_id'])[:6])}]"
    for p in all_prompts_sorted
]

selected_idx = st.sidebar.radio(
    "Saved Prompts", list(range(len(sidebar_options))),
    format_func=lambda i: sidebar_options[i] if sidebar_options else "",
)


# --- Add this fix ---
if "last_selected_idx" not in st.session_state:
    st.session_state["last_selected_idx"] = selected_idx

if st.session_state["last_selected_idx"] != selected_idx:
    st.session_state["last_selected_idx"] = selected_idx
    st.session_state.pop('fields', None)
    st.experimental_rerun()

# Custom CSS for sidebar
st.markdown(
    """
    <style>
    .sidebar-content span, .sidebar-content strong {
        font-size: 14px !important;
    }
    .sidebar-content {
        margin-bottom: 10px;
        display: block;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Render sidebar markdown (ignore for the radio; just pretty display)
for idx, md in enumerate(sidebar_options[1:], start=1):
    st.sidebar.markdown(f'<div class="sidebar-content">{md}</div>', unsafe_allow_html=True)
# ---- New Prompt Template ----
def new_prompt_template():
    return {
        "title": "",
        "description": "",
        "status": "Draft",
        "model": "gpt-4o",
        "tags": [],
        "prompt_body": "",
        "examples": [],
        "version_history": []
    }

is_new = selected_idx == 0
selected_prompt = None if is_new else all_prompts[selected_idx - 1]

# ---- Main Editor ----
if is_new:
    st.title("➕ Create New Prompt")
    doc = new_prompt_template()
    is_editable = True
else:
    doc = prompt_collection.find_one({"_id": selected_prompt["_id"]}) if selected_prompt else new_prompt_template()
    st.title(f"🧾 {doc.get('title', 'Prompt Details')}")
    is_editable = True  # Could add view-only mode if you want

# ---- Editing State ----
if 'fields' not in st.session_state or is_new:
    st.session_state['fields'] = {
        'title': doc.get('title', ''),
        'description': doc.get('description', ''),
        'status': doc.get('status', 'Draft'),
        'model': doc.get('model', 'gpt-4o'),
        'tags': doc.get('tags', []),
        'prompt_body': doc.get('prompt_body', ''),
        'examples': doc.get('examples', []),
        'version_history': doc.get('version_history', [])
    }
fields = st.session_state['fields']

# ---- Form UI ----
col1, col2 = st.columns(2)
with col1:
    fields['title'] = st.text_input("Title", value=fields['title'], key='title')
    fields['description'] = st.text_area("Description", value=fields['description'], key='description')
with col2:
    fields['status'] = st.selectbox("Status", ["Draft", "Approved", "Deprecated"], index=["Draft", "Approved", "Deprecated"].index(fields['status']), key='status')
    fields['model'] = st.selectbox("Model Used", ["gpt-4", "gpt-4o", "gpt-3.5-turbo"], index=["gpt-4", "gpt-4o", "gpt-3.5-turbo"].index(fields['model']), key='model')
    fields['tags'] = st.multiselect("Tags", ["QA", "Banking", "User Story", "Chat", "NLP"], default=fields['tags'], key='tags')

st.markdown("### 🧠 Prompt Text")
fields['prompt_body'] = st.text_area("", value=fields['prompt_body'], height=300, label_visibility="collapsed", key='prompt_body')

# ---- Examples Section ----
st.markdown("### 📄 Example Input/Output")
exs = fields['examples']
if st.button("Add Example"):
    exs.append({"input": "", "output": ""})
for i, ex in enumerate(exs):
    with st.expander(f"Example {i+1}", expanded=False):
        ex['input'] = st.text_area(f"Input Example {i+1}", value=ex.get('input', ''), key=f'input_ex_{i}')
        ex['output'] = st.text_area(f"Output Example {i+1}", value=ex.get('output', ''), key=f'output_ex_{i}')
        if st.button(f"Delete Example {i+1}"):
            exs.pop(i)
            st.experimental_rerun()
fields['examples'] = exs

# ---- Version History Section ----
st.markdown("### 🕓 Version History")
vhs = fields['version_history']
if 'open_expander_idx' not in st.session_state:
    st.session_state['open_expander_idx'] = None

if st.button("Add Version Note"):
    today_str = date.today().strftime('%Y-%m-%d')
    vhs.insert(0, {"version": f"v{len(vhs)+1}.0", "date": today_str, "note": ""})
    st.session_state['open_expander_idx'] = 0  # Open the new expander at the top

for i, v in enumerate(vhs):
    expanded = (st.session_state.get('open_expander_idx') == i)
    with st.expander(f"{v['version']} ({v.get('date','')})", expanded=expanded):
        new_ver = st.text_input(f"Version {i+1}", value=v.get('version', f"v{i+1}.0"), key=f'ver_{i}')
        new_date = st.text_input(f"Date {i+1}", value=v.get('date', ''), key=f'verdate_{i}')
        new_note = st.text_area(f"Note {i+1}", value=v.get('note', ''), key=f'vernote_{i}')
        # Save edit back
        v['version'] = new_ver
        v['date'] = new_date
        v['note'] = new_note
        if st.button(f"Delete Version {i+1}"):
            vhs.pop(i)
            if st.session_state.get('open_expander_idx') == i:
                st.session_state['open_expander_idx'] = None
            st.experimental_rerun()
        # If user types in this expander, keep it open
        if expanded:
            st.session_state['open_expander_idx'] = i
fields['version_history'] = vhs

st.markdown("---")
col3, col4, col5, col6 = st.columns(4)

# ---- Save Logic ----
def get_new_prompt_id():
    # Generates new PRM-### ID (basic, demo only!)
    last = prompt_collection.find_one(sort=[("prompt_id", -1)])
    if last and 'prompt_id' in last:
        try:
            n = int(last['prompt_id'].split('-')[1]) + 1
            return f"PRM-{n:03d}"
        except Exception:
            pass
    return "PRM-001"

save_error = None

with col3:
    if st.button("💾 Save Draft"):
        try:
            data_to_save = fields.copy()
            if is_new:
                data_to_save['prompt_id'] = get_new_prompt_id()
                prompt_collection.insert_one(data_to_save)
                st.success("Prompt created!")
                st.session_state.pop('fields')
                st.experimental_rerun()
            else:
                prompt_collection.update_one({"_id": doc["_id"]}, {"$set": data_to_save})
                st.success("Prompt updated!")
                st.session_state.pop('fields')
                st.experimental_rerun()
        except Exception as e:
            save_error = str(e)
with col4:
    if st.button("✅ Approve"):
        try:
            fields['status'] = "Approved"
            data_to_save = fields.copy()
            if is_new:
                data_to_save['prompt_id'] = get_new_prompt_id()
                prompt_collection.insert_one(data_to_save)
                st.success("Prompt approved and created!")
                st.session_state.pop('fields')
                st.experimental_rerun()
            else:
                prompt_collection.update_one({"_id": doc["_id"]}, {"$set": data_to_save})
                st.success("Prompt approved!")
                st.session_state.pop('fields')
                st.experimental_rerun()
        except Exception as e:
            save_error = str(e)
with col5:
    if not is_new and st.button("🗑️ Delete"):
        try:
            prompt_collection.delete_one({"_id": doc["_id"]})
            st.success("Prompt deleted!")
            st.session_state.pop('fields')
            st.experimental_rerun()
        except Exception as e:
            save_error = str(e)
with col6:
    if st.button("⬅ Back to List"):
        st.session_state.pop('fields')
        st.experimental_rerun()

if save_error:
    st.error(f"Error saving to MongoDB: {save_error}")
