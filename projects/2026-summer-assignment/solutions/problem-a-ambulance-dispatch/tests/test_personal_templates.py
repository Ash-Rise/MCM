from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[3]
PROFILE_PATH = PROJECT_ROOT / "templates" / "personal-paper-profile.yaml"
PLAYBOOK_PATH = PROJECT_ROOT / "templates" / "personal-modeling-playbook.md"


def test_machine_profile_encodes_dual_markdown_targets():
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    markdown = profile["markdown"]

    assert profile["profile_version"] == 1.1
    assert markdown["source_target"]["dialect"] == "pandoc_markdown"
    assert markdown["source_target"]["editable"] is True
    assert markdown["github_preview_target"]["dialect"] == (
        "github_flavored_markdown"
    )
    assert markdown["github_preview_target"]["editable"] is False
    assert markdown["github_preview_target"]["inline_math_delimiter"] == "$`...`$"
    assert markdown["github_preview_target"]["citation_superscript_pattern"] == (
        "<sup>[n]</sup>"
    )
    assert markdown["generator"]["check_flag"] == "--check"
    assert markdown["generator"]["preserve_fenced_code_blocks"] is True

    assert profile["release"]["required_artifacts"] == [
        "pandoc_markdown_source",
        "generated_github_preview",
        "docx",
        "conversion_manifest",
    ]


def test_personal_workflow_records_verified_rule_promotion_contract():
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    playbook = PLAYBOOK_PATH.read_text(encoding="utf-8")
    promotion = profile["workflow"]["reusable_rule_promotion"]

    assert promotion["enabled"] is True
    assert promotion["user_authorized"] is True
    assert promotion["record_source_and_date"] is True
    assert promotion["never_promote_one_off_workarounds"] is True
    assert len(promotion["requirements"]) == 4
    assert promotion["registry"] == [
        {
            "id": "markdown_dual_target",
            "added_on": "2026-08-13",
            "source": "v2.4_github_renderer_compatibility_audit",
            "evidence": [
                "github_markdown_api",
                "reproducible_preview_tests",
            ],
            "scope": "pandoc_docx_source_and_github_online_preview",
        },
        {
            "id": "separate_paper_and_tooling_changelogs",
            "added_on": "2026-08-13",
            "source": "v2.4_release_timestamp_boundary_audit",
            "evidence": ["formal_docx_unchanged", "git_commit_timeline"],
            "scope": "release_notes_and_workflow_template_changelog",
        },
    ]

    release = profile["release"]
    assert release["paper_timestamp_changes_only_with_formal_paper_deliverable"] is True
    assert release["tooling_and_template_changelog_separate"] is True

    assert "Markdown双目标排版" in playbook
    assert playbook.startswith("# 个性化数模工作流与论文模板 v1.1")
    assert "我们的个性化数模工作流与论文模板" not in playbook
    assert "优质规则自动沉淀机制" in playbook
    assert "真实论文、官方渲染器或可复现测试" in playbook
    assert "能跨题目复用" in playbook
    assert "记录来源和日期" in playbook
    assert "不得自动提升为长期规则" in playbook
    assert "工作流与模板更新记录" in playbook


def test_paper_release_time_is_separate_from_tooling_changelog():
    readme_zh = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (REPOSITORY_ROOT / "README_EN.md").read_text(encoding="utf-8")

    assert "### v2.4（2026-08-13 04:39 UTC+8）" in readme_zh
    assert "### v2.4 (2026-08-13 04:39 UTC+8)" in readme_en
    assert "## 工作流与模板更新记录" in readme_zh
    assert "## Workflow and Template Changelog" in readme_en
    assert "### 2026-08-13 13:03 UTC+8 — 个性化模板 v1.1" in readme_zh
    assert "### 2026-08-13 13:03 UTC+8 — Personalized Template v1.1" in readme_en
    assert "这些变更不修改论文版本的发行时间" in readme_zh
    assert "These changes do not modify the paper release timestamp" in readme_en
