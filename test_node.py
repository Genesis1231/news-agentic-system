import asyncio
import argparse
from backend.services.workflow import FlowOrchestrator
from backend.core.database import DataInterface

from dotenv import load_dotenv


load_dotenv()

async def run_test(test_id: int):

    orchestrator = FlowOrchestrator()
    result = await orchestrator.immediate(test_id)

    if result is None:
        print("Workflow returned None — check logs.")
        return

    print(f"\n{'='*60}")
    print(f"Status: {result.get('status', 'Unknown')}")
    print(f"{'='*60}")

    # Print draft script if available
    draft = result.get("draft")
    if draft:
        print(f"\n--- DRAFT SCRIPT ---\n{draft}")

    # Print review if available
    review = result.get("review")
    if review:
        print(f"\n--- REVIEW ---\n{review}")

    # Print output (finalized news items)
    output = result.get("output")
    if output:
        for i, item in enumerate(output):
            print(f"\n--- OUTPUT [{i}] ---")
            if hasattr(item, 'script'):
                print(f"Depth: {item.depth}")
                print(f"Script:\n{item.script}")
            elif isinstance(item, dict):
                print(f"Depth: {item.get('depth')}")
                print(f"Script:\n{item.get('script')}")
            else:
                print(item)

    # Print the full result keys for debugging
    print(f"\n--- STATE KEYS: {list(result.keys())} ---")


# Execute the async function

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run test node with specified ID')
    parser.add_argument('-id', '--id', type=int, required=True, help='ID to run test with')
    args = parser.parse_args()

    asyncio.run(run_test(args.id))
