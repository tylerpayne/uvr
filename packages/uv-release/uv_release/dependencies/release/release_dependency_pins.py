"""ReleaseDependencyPins: internal dep version pins after release bump."""

from __future__ import annotations

from diny import singleton, provider

from ...types.base import Frozen
from ...types.pin import Pin
from .release_versions import ReleaseVersions
from ..shared.workspace_packages import WorkspacePackages
from ...utils.versioning import compute_dependency_pins


@singleton
class ReleaseDependencyPins(Frozen):
    """Pins to apply after post-release version bumping."""

    items: list[Pin] = []


@provider(ReleaseDependencyPins)
def provide_release_dependency_pins(
    release_versions: ReleaseVersions,
    workspace_packages: WorkspacePackages,
) -> ReleaseDependencyPins:
    # Pins reference the just-released versions, not the post-release
    # next-dev versions. Pinning to a next-dev (e.g. 0.2.1.dev0 ahead of
    # an unreleased 0.2.1) would point consumers at a version that does
    # not exist yet. Under the conditional rule in compute_dependency_pins,
    # this is typically a no-op: any dependent's pin that already accepts
    # the just-released version stays untouched. It only fires as a safety
    # net when a release lands at a version outside an existing pin range
    # without a prior `uvr version --bump`.
    pins = compute_dependency_pins(release_versions.items, workspace_packages.items)
    return ReleaseDependencyPins(items=pins)
