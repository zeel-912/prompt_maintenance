# Prompt Maintenance

This Streamlit application lets you create and manage prompt templates stored in MongoDB.

## Setup

1. Install Python dependencies:
   ```bash
   pip install streamlit pymongo
   ```
2. Ensure MongoDB is running and accessible.
3. Optionally set the `MONGODB_URI` environment variable to override the default
   `mongodb://localhost:27017/` connection string.

## Tags

When editing a prompt you can select existing tags from the database or add new
ones by typing them comma-separated in the **Custom Tags** field.

## Running the App

```bash
streamlit run app.py
```
