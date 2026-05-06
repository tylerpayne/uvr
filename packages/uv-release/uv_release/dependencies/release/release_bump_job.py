"""ReleaseBumpJob: post-release version bumps, dep pins, baseline tags, push."""

from __future__ import annotations

from diny import singleton, provider

from .release_bump_versions import ReleaseBumpVersions
from ...commands import (
    CommitCommand,
    ConfigureGitIdentityCommand,
    CreateTagCommand,
    PinDepsCommand,
    PushCommand,
    SetVersionCommand,
    SyncLockfileCommand,
)
from .release_dependency_pins import ReleaseDependencyPins
from ...types.job import Job
from ..params.no_commit import NoCommit
from ..params.no_push import NoPush
from ..params.release_target import ReleaseTarget
from ..shared.workspace_packages import WorkspacePackages
from ...types.tag import Tag


@singleton
class ReleaseBumpJob(Job):
    """Post-release bump: set next versions, pin deps, tag baselines, push."""


@provider(ReleaseBumpJob)
def provide_release_bump_job(
    bump_versions: ReleaseBumpVersions,
    dependency_pins: ReleaseDependencyPins,
    workspace_packages: WorkspacePackages,
    release_target: ReleaseTarget,
    no_commit: NoCommit,
    no_push: NoPush,
) -> ReleaseBumpJob:
    if not bump_versions.items:
        return ReleaseBumpJob(name="bump")

    is_local = release_target.value == "local"

    commands: list[
        ConfigureGitIdentityCommand
        | SetVersionCommand
        | PinDepsCommand
        | SyncLockfileCommand
        | CommitCommand
        | CreateTagCommand
        | PushCommand
    ] = []

    if not is_local:
        commands.append(ConfigureGitIdentityCommand(label="Configure git identity"))

    for name, next_version in bump_versions.items.items():
        pkg = workspace_packages.items[name]
        commands.append(
            SetVersionCommand(
                label=f"Bump {name} to {next_version.raw}",
                package_path=pkg.path,
                version=next_version.raw,
            )
        )

    for pin in dependency_pins.items:
        commands.append(
            PinDepsCommand(
                label=f"Pin deps in {pin.package_path}",
                package_path=pin.package_path,
                pins=pin.pins,
            )
        )

    commands.append(SyncLockfileCommand(label="Sync lockfile"))

    skip_commit = is_local and no_commit.value
    skip_push = is_local and no_push.value

    if not skip_commit:
        body_lines = [f"  {n}: {v.raw}" for n, v in bump_versions.items.items()]
        commands.append(
            CommitCommand(
                label="Commit version bumps",
                message="chore: bump to next dev versions",
                body="\n".join(body_lines),
            )
        )

        for name, version in bump_versions.items.items():
            baseline_tag = Tag.baseline_tag_name(name, version)
            commands.append(
                CreateTagCommand(
                    label=f"Baseline {baseline_tag}", tag_name=baseline_tag
                )
            )

        if not skip_push:
            commands.append(
                PushCommand(label="Push", follow_tags=True, pull_rebase=True)
            )

    return ReleaseBumpJob(name="bump", commands=commands)  # type: ignore[arg-type]
