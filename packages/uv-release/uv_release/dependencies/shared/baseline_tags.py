"""BaselineTags: git tags to diff against for change detection."""

from __future__ import annotations

from packaging.version import Version as PkgVersion

from diny import singleton, provider

from ...types.base import Frozen
from .git_repo import GitRepo
from ...types.tag import Tag
from ...types.version import Version, VersionState
from .workspace_packages import WorkspacePackages


@singleton
class BaselineTags(Frozen):
    """Package name -> baseline Tag for diffing."""

    items: dict[str, Tag] = {}


@provider(BaselineTags)
def provide_baseline_tags(
    workspace_packages: WorkspacePackages, git_repo: GitRepo
) -> BaselineTags:
    # Diff anchors for change detection. Missing baseline = initial release.
    items: dict[str, Tag] = {}
    for name, pkg in workspace_packages.items.items():
        tag = _find_baseline_tag(name, pkg.version, git_repo)
        if tag is not None:
            items[name] = tag
    return BaselineTags(items=items)


def _find_baseline_tag(name: str, version: Version, repo: GitRepo) -> Tag | None:
    state = version.state

    # dev0: try explicit baseline tag first, fall back to previous release.
    if state in (
        VersionState.DEV0_STABLE,
        VersionState.DEV0_PRE,
        VersionState.DEV0_POST,
    ):
        tag_name = Tag.baseline_tag_name(name, version)
        return repo.resolve_tag(name, tag_name, is_baseline=True) or _previous_release(
            name, version, repo
        )

    # devK: use the dev0 baseline tag as consistent anchor for the cycle.
    if state in (
        VersionState.DEVK_STABLE,
        VersionState.DEVK_PRE,
        VersionState.DEVK_POST,
    ):
        dev0 = version.with_dev(0)
        tag_name = Tag.baseline_tag_name(name, dev0)
        return repo.resolve_tag(name, tag_name, is_baseline=True) or _previous_release(
            name, version, repo
        )

    # Clean: prefer the dev0 baseline tag for this version if one exists —
    # that's the cycle anchor (e.g. v0.34.2 was just stripped from
    # 0.34.2.dev0, the v0.34.2.dev0-base tag still marks where the cycle
    # started). Fall back to the previous release tag if no baseline
    # exists (initial release, or pre-`uvr` history).
    if state in (
        VersionState.CLEAN_STABLE,
        VersionState.CLEAN_PREN,
        VersionState.CLEAN_PRE0,
    ):
        # `with_dev(0)` preserves pre_kind so `0.34.2a0` resolves to
        # `0.34.2a0.dev0-base`, not `0.34.2.dev0-base`.
        dev0 = version.with_dev(0)
        tag_name = Tag.baseline_tag_name(name, dev0)
        return repo.resolve_tag(name, tag_name, is_baseline=True) or _previous_release(
            name, version, repo
        )

    # Post-release: diff against the base stable release.
    if state in (VersionState.CLEAN_POST0, VersionState.CLEAN_POSTM):
        base_version = Version.build(version.base)
        tag_name = Tag.release_tag_name(name, base_version)
        return repo.resolve_tag(name, tag_name, is_baseline=False)

    msg = f"Unhandled version state: {state}"
    raise AssertionError(msg)


def _previous_release(name: str, version: Version, repo: GitRepo) -> Tag | None:
    """Find the previous release tag and resolve it to a Tag."""
    # Dev versions use base as upper bound since they've never been released.
    target = PkgVersion(version.base if version.is_dev else version.raw)
    tag_name = repo.find_previous_release_tag(name, target)
    if tag_name is None:
        return None
    return repo.resolve_tag(name, tag_name, is_baseline=False)
