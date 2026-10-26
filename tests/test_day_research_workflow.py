from pathlib import Path


def test_day_research_workflow_writes_to_non_deploy_branch():
    workflow = Path(".github/workflows/day-research.yml").read_text(encoding="utf-8")

    assert 'branch="research/day-research-notes"' in workflow
    assert 'git push origin "HEAD:$branch"' in workflow
    assert "git push\n" not in workflow
    assert "git push origin main" not in workflow
