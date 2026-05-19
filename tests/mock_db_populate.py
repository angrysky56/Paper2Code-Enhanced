import os
import sys

# Ensure codes/ is on the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "codes")))

from db import init_db, create_run, complete_run, write_stage_result, write_execution_trial

def populate_mock_db():
    print("Populating Mock DB at outputs/mock_paper2code.db...")
    
    os.environ["DB_PATH"] = "outputs/mock_paper2code.db"
    if os.path.exists("outputs/mock_paper2code.db"):
        os.remove("outputs/mock_paper2code.db")
        
    init_db()
    
    # ----------------------------------------------------
    # Run 1: Successful Transformer Implementation
    # ----------------------------------------------------
    run_1 = create_run(
        paper_name="Attention Is All You Need",
        model_used="o3-mini",
        output_dir="outputs/attention"
    )
    
    # Stages for Run 1
    write_stage_result(
        run_1, "planning", success=True,
        tokens_in=5000, tokens_out=1500, cost_usd=0.015,
        output_path="outputs/attention/planning.json",
        messages=[{"role": "user", "content": "Plan Transformer"}],
        model_used="o3-mini"
    )
    write_stage_result(
        run_1, "analyzing", success=True,
        tokens_in=6500, tokens_out=2200, cost_usd=0.020,
        output_path="outputs/attention/analysis.json",
        messages=[{"role": "user", "content": "Analyze architecture"}],
        model_used="o3-mini"
    )
    write_stage_result(
        run_1, "coding", success=True,
        tokens_in=12000, tokens_out=4500, cost_usd=0.045,
        output_path="outputs/attention/model.py",
        messages=[{"role": "user", "content": "Write PyTorch code"}],
        model_used="o3-mini"
    )
    
    # Trials for Run 1 (Takes 2 attempts to pass)
    write_execution_trial(
        run_1, attempt_num=1, stdout="AttributeError: module 'torch' has no attribute 'some_deprecated_fn'",
        stderr="Traceback...", returncode=1, timed_out=False, elapsed_seconds=2.1,
        code_dir="outputs/attention"
    )
    write_stage_result(
        run_1, "debugging", success=True,
        tokens_in=8000, tokens_out=800, cost_usd=0.022,
        output_path="outputs/attention/model.py",
        messages=[{"role": "user", "content": "Fix AttributeError"}],
        model_used="o3-mini"
    )
    write_execution_trial(
        run_1, attempt_num=2, stdout="All 15 tests passed successfully!",
        stderr="", returncode=0, timed_out=False, elapsed_seconds=3.5,
        code_dir="outputs/attention"
    )
    
    complete_run(run_1, status="completed")
    
    # ----------------------------------------------------
    # Run 2: Failed ResNet Implementation
    # ----------------------------------------------------
    run_2 = create_run(
        paper_name="Deep Residual Learning",
        model_used="gpt-4o",
        output_dir="outputs/resnet"
    )
    
    write_stage_result(
        run_2, "planning", success=True,
        tokens_in=4000, tokens_out=1200, cost_usd=0.026,
        output_path="outputs/resnet/planning.json",
        messages=[{"role": "user", "content": "Plan ResNet"}],
        model_used="gpt-4o"
    )
    write_stage_result(
        run_2, "analyzing", success=True,
        tokens_in=5000, tokens_out=1800, cost_usd=0.034,
        output_path="outputs/resnet/analysis.json",
        messages=[{"role": "user", "content": "Analyze ResNet layers"}],
        model_used="gpt-4o"
    )
    write_stage_result(
        run_2, "coding", success=False,
        tokens_in=10000, tokens_out=500, cost_usd=0.052,
        output_path="",
        messages=[{"role": "user", "content": "Write PyTorch code for ResNet"}],
        model_used="gpt-4o"
    )
    
    complete_run(run_2, status="failed")

    # ----------------------------------------------------
    # Run 3: Running Vision Transformer (ViT)
    # ----------------------------------------------------
    run_3 = create_run(
        paper_name="An Image is Worth 16x16 Words",
        model_used="o3-mini",
        output_dir="outputs/vit"
    )
    
    write_stage_result(
        run_3, "planning", success=True,
        tokens_in=6000, tokens_out=1800, cost_usd=0.018,
        output_path="outputs/vit/planning.json",
        messages=[{"role": "user", "content": "Plan ViT"}],
        model_used="o3-mini"
    )
    write_stage_result(
        run_3, "analyzing", success=True,
        tokens_in=7500, tokens_out=2500, cost_usd=0.023,
        output_path="outputs/vit/analysis.json",
        messages=[{"role": "user", "content": "Analyze ViT patches"}],
        model_used="o3-mini"
    )
    
    print("Mock DB generation COMPLETE!")

if __name__ == "__main__":
    populate_mock_db()
