import os
import sys

# Ensure codes/ is on the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "codes")))

from db import init_db, create_run, complete_run, write_stage_result, write_execution_trial, get_run_summary, get_all_runs

def test_db():
    print("Testing DB Persistence Layer...")
    
    # Override DB_PATH to a temporary test file
    os.environ["DB_PATH"] = "outputs/test_paper2code.db"
    if os.path.exists("outputs/test_paper2code.db"):
        os.remove("outputs/test_paper2code.db")
        
    init_db()
    
    print("1. Creating idempotent runs...")
    run_id = create_run(paper_name="TransformerTest", model_used="o3-mini", output_dir="outputs/TransformerTest")
    assert run_id > 0, "Failed to create run"
    print(f"   Created Run ID: {run_id}")
    
    # Try to resume the run idempotently
    run_id_resume = create_run(paper_name="TransformerTest", model_used="o3-mini", output_dir="outputs/TransformerTest")
    assert run_id_resume == run_id, f"Idempotent resume failed: expected {run_id}, got {run_id_resume}"
    print(f"   Idempotent resume success. Reused Run ID: {run_id_resume}")
    
    print("2. Writing stage results...")
    stage_id = write_stage_result(
        run_id,
        "planning",
        success=True,
        tokens_in=100,
        tokens_out=200,
        cost_usd=0.005,
        output_path="outputs/TransformerTest/planning_trajectories.json",
        messages=[{"role": "user", "content": "Hello LLM"}],
        model_used="o3-mini"
    )
    assert stage_id > 0, "Failed to write stage result"
    print(f"   Created Stage Result ID: {stage_id}")
    
    print("3. Writing execution trials...")
    trial_id = write_execution_trial(
        run_id,
        attempt_num=1,
        stdout="Test passed",
        stderr="",
        returncode=0,
        timed_out=False,
        elapsed_seconds=1.5,
        code_dir="outputs/TransformerTest"
    )
    assert trial_id > 0, "Failed to write execution trial"
    print(f"   Created Execution Trial ID: {trial_id}")
    
    print("4. Completing run and verifying aggregates...")
    complete_run(run_id, status="completed")
    
    summary = get_run_summary(run_id)
    print("   Run Summary:")
    print(f"     Status: {summary['status']}")
    print(f"     Total Cost: {summary['total_cost']}")
    print(f"     Total Tokens In: {summary['total_tokens_in']}")
    print(f"     Total Tokens Out: {summary['total_tokens_out']}")
    print(f"     Stages Executed: {[s['stage_name'] for s in summary['stages']]}")
    print(f"     Trials Run: {[t['attempt_num'] for t in summary['trials']]}")
    
    assert summary["status"] == "completed"
    assert summary["total_cost"] == 0.005
    assert summary["total_tokens_in"] == 100
    assert summary["total_tokens_out"] == 200
    
    all_runs = get_all_runs()
    assert len(all_runs) == 1
    print("All persistence layer checks PASSED successfully!")
    
    # Clean up test DB file
    if os.path.exists("outputs/test_paper2code.db"):
        os.remove("outputs/test_paper2code.db")

if __name__ == "__main__":
    test_db()
