"""ChangedPackages: which packages changed since their baselines."""

from __future__ import annotations

from diny import singleton, provider

from ...types.base import Frozen
from .baseline_tags import BaselineTags
from .git_repo import GitRepo
from .workspace_packages import WorkspacePackages


@singleton
class ChangedPackages(Frozen):
    """Package name -> reason it changed."""

    reasons: dict[str, str] = {}
    commit_logs: dict[str, str] = {}

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self.reasons.keys())


@provider(ChangedPackages)
def provide_changed_packages(
    workspace_packages: WorkspacePackages,
    baseline_tags: BaselineTags,
    git_repo: GitRepo,
) -> ChangedPackages:
    # Detection is purely file-based. A dependent of a changed package is
    # NOT marked dirty here. The expected workflow for cross-package bumps
    # is `uvr version --bump minor` (or major), which writes pin updates
    # into dependents' pyproject.toml and so makes them file-changed in
    # the same release cycle. Patch-level releases do not break pin
    # ranges, so dependents stay clean.
    head = git_repo.head_commit()
    packages = workspace_packages.items

    reasons: dict[str, str] = {}
    commit_logs: dict[str, str] = {}

    for name, pkg in packages.items():
        baseline = baseline_tags.items.get(name)
        if baseline is None:
            reasons[name] = "initial release"
            continue
        if git_repo.path_changed(baseline.commit, head, pkg.path):
            reasons[name] = "files changed"
            commit_logs[name] = git_repo.commit_log(baseline.commit, head, pkg.path)

    sorted_names = sorted(reasons.keys())
    return ChangedPackages(
        reasons={n: reasons[n] for n in sorted_names},
        commit_logs={n: commit_logs[n] for n in sorted_names if n in commit_logs},
    )
