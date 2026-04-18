import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def check_training_data():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_ANON_KEY not set in .env")
        return

    supabase = create_client(url, key)
    try:
        res = supabase.table("zone_snapshots").select("id", count="exact").execute()
        print(f"Total Snapshots Available for Training: {res.count}")
    except Exception as e:
        print(f"Error querying data: {e}")

if __name__ == "__main__":
    check_training_data()
