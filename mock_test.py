import asyncio
import json
import os
from main import run_pipeline

async def test_end_to_end():
    print("Starting 1:1 Mentoring CRM Pipeline E2E Test...")
    
    # 1. Load Database IDs
    config_path = os.path.join(os.path.dirname(__file__), 'db_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            db_ids = json.load(f)
    except FileNotFoundError:
        print("Error: db_config.json not found.")
        return
        
    print("Success: Database config loaded.")

    # 2. Mock Data Setup
    mock_student_name = "Hong Gildong"
    
    mock_email_text = """
    In today's mentoring session (session 3), we focused on the AI service proposal.
    The problem definition is much sharper. You correctly identified that users struggle to read text when busy.
    However, the diagram assignment is not yet submitted. Please submit it by next Tuesday.
    """
    
    mock_memo_id = "fake_memo_block_id"
    
    print(f"Sending mock data for {mock_student_name} to pipeline...")
    
    try:
        await run_pipeline(
            email_text=mock_email_text,
            memo_id=mock_memo_id,
            student_name=mock_student_name,
            db_ids=db_ids
        )
        print("Test completed successfully! Check your Notion Master CRM.")
    except Exception as e:
        import traceback
        print(f"Error occurred: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test_end_to_end())
