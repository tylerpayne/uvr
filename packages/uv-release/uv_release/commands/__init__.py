"""Command types. Each is an atomic executable step."""

from typing import Annotated

from pydantic import Discriminator

from .base import Command
from .build import BuildCommand
from .dispatch import DispatchWorkflowCommand
from .download import DownloadRunArtifactsCommand, DownloadWheelsCommand
from .fetch import FetchSkillBasesCommand, FetchWorkflowBaseCommand
from .file import MakeDirectoryCommand, RemoveDirectoryCommand, WriteFileCommand
from .git import (
    CommitCommand,
    ConfigureGitIdentityCommand,
    PullRebaseCommand,
    PushCommand,
)
from .group import CommandGroup
from .install import InstallWheelsCommand
from .merge import MergeUpgradeCommand
from .publish import PublishToIndexCommand
from .release import CreateReleaseCommand
from .shell import CreateTagCommand, ShellCommand
from .sync import SyncLockfileCommand
from .toml import UpdateTomlCommand, WriteUvrSectionCommand
from .version import PinDepsCommand, SetVersionCommand

# Discriminated union for polymorphic Pydantic serialization via the "type" field.
AnyCommand = Annotated[
    ShellCommand
    | CreateTagCommand
    | SetVersionCommand
    | PinDepsCommand
    | BuildCommand
    | DownloadWheelsCommand
    | DownloadRunArtifactsCommand
    | CreateReleaseCommand
    | PublishToIndexCommand
    | WriteFileCommand
    | MakeDirectoryCommand
    | RemoveDirectoryCommand
    | UpdateTomlCommand
    | WriteUvrSectionCommand
    | FetchWorkflowBaseCommand
    | FetchSkillBasesCommand
    | MergeUpgradeCommand
    | InstallWheelsCommand
    | ConfigureGitIdentityCommand
    | CommitCommand
    | PullRebaseCommand
    | PushCommand
    | SyncLockfileCommand
    | DispatchWorkflowCommand
    | CommandGroup,
    Discriminator("type"),
]

__all__ = [
    "AnyCommand",
    "BuildCommand",
    "Command",
    "CommandGroup",
    "CommitCommand",
    "ConfigureGitIdentityCommand",
    "CreateReleaseCommand",
    "CreateTagCommand",
    "DispatchWorkflowCommand",
    "DownloadRunArtifactsCommand",
    "DownloadWheelsCommand",
    "FetchSkillBasesCommand",
    "FetchWorkflowBaseCommand",
    "InstallWheelsCommand",
    "MakeDirectoryCommand",
    "MergeUpgradeCommand",
    "PinDepsCommand",
    "PublishToIndexCommand",
    "PullRebaseCommand",
    "PushCommand",
    "RemoveDirectoryCommand",
    "SetVersionCommand",
    "ShellCommand",
    "SyncLockfileCommand",
    "UpdateTomlCommand",
    "WriteFileCommand",
    "WriteUvrSectionCommand",
]
