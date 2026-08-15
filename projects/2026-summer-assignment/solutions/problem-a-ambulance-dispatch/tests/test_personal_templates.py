from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[3]
SOURCE_ROOT = PROJECT_ROOT / "src"
PROFILE_PATH = PROJECT_ROOT / "templates" / "personal-paper-profile.yaml"
PLAYBOOK_PATH = PROJECT_ROOT / "templates" / "personal-modeling-playbook.md"


def test_machine_profile_encodes_single_pandoc_markdown_source():
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    markdown = profile["markdown"]

    assert profile["profile_version"] == 1.3
    assert markdown["source_target"]["dialect"] == "pandoc_markdown"
    assert markdown["source_target"]["editable"] is True
    assert markdown["publish_derived_github_preview"] is False
    assert "github_preview_target" not in markdown
    assert "generator" not in markdown

    assert profile["release"]["required_artifacts"] == [
        "pandoc_markdown_source",
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
            "status": "retired_by_user_decision",
            "retired_on": "2026-08-13",
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
        {
            "id": "exact_manual_word_table_lock",
            "added_on": "2026-08-13",
            "source": "v2.5_wps_table_lock_regression",
            "evidence": [
                "user_corrected_v2.5_docx",
                "complete_table_ooxml_save_reload_test",
                "affected_page_render_review",
            ],
            "scope": "manual_word_table_baselines_and_docx_regeneration",
        },
        {
            "id": "source_file_purpose_header",
            "added_on": "2026-08-15",
            "source": "problem_a_src_inventory_review",
            "evidence": [
                "purpose_headers_added_to_tracked_source_files",
                "python_compileall_passed",
                "independent_p2_source_header_review_passed",
            ],
            "scope": "modeling_project_source_files",
        },
    ]

    table_lock = profile["tables"]["manual_word_baseline"]
    assert table_lock["final_release_lock_mode"] == "complete_table_ooxml_only"
    assert table_lock["layout_only_mode"] == "transitional_draft_only"
    assert table_lock["exact_table_replacement_must_be_last_table_operation"] is True
    assert table_lock["require_save_close_reload_before_comparison"] is True
    assert table_lock["require_complete_table_xml_regression"] is True
    assert table_lock["require_semantic_alignment_assertions"] is True

    release = profile["release"]
    assert release["paper_timestamp_changes_only_with_formal_paper_deliverable"] is True
    assert release["tooling_and_template_changelog_separate"] is True

    assert "Pandoc Markdown单一正文源" in playbook
    assert playbook.startswith("# 个性化数模工作流与论文模板 v1.3")
    assert "我们的个性化数模工作流与论文模板" not in playbook
    assert "优质规则自动沉淀机制" in playbook
    assert "真实论文、官方渲染器或可复现测试" in playbook
    assert "能跨题目复用" in playbook
    assert "记录来源和日期" in playbook
    assert "不得自动提升为长期规则" in playbook
    assert "工作流与模板更新记录" in playbook


def test_source_files_require_first_line_purpose_comment():
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    playbook = PLAYBOOK_PATH.read_text(encoding="utf-8")
    source_header = profile["implementation"]["source_file_purpose_header"]

    assert source_header == {
        "required": True,
        "scope": "src_source_files",
        "extensions": [".py", ".m"],
        "position": "first_line",
        "language": "concise_chinese",
        "comment_markers": {"python": "#", "matlab": "%"},
        "describe": ["file_purpose", "pipeline_role"],
        "forbid": ["implementation_details", "parameter_lists", "change_history"],
    }
    assert "每个源码文件的首行" in playbook
    assert "文件用途及其在计算链中的职责" in playbook
    assert "字节码缓存不属于源码，不纳入检查" in playbook

    source_files = sorted(
        path
        for extension in source_header["extensions"]
        for path in SOURCE_ROOT.rglob(f"*{extension}")
    )
    assert source_files
    marker_by_extension = {
        ".py": source_header["comment_markers"]["python"],
        ".m": source_header["comment_markers"]["matlab"],
    }
    for source_file in source_files:
        first_line = source_file.read_text(encoding="utf-8").splitlines()[0]
        marker = marker_by_extension[source_file.suffix]
        assert first_line.startswith(marker), source_file
        description = first_line[len(marker):].strip()
        assert description, source_file
        assert any("\u4e00" <= char <= "\u9fff" for char in description), source_file


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
    assert "### 2026-08-15 14:51 UTC+8 — 源码用途注释纳入个性化模板" in readme_zh
    assert "### 2026-08-15 14:51 UTC+8 — Source Purpose Headers Added to the Personalized Template" in readme_en
