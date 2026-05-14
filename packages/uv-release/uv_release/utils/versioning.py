"""Pure version computations. No DI, no I/O."""

from __future__ import annotations

from ..types.bump_kind import BumpKind
from ..types.package import Package
from ..types.pin import Pin
from ..types.version import Version


def compute_release_version(version: Version, *, dev_release: bool = False) -> Version:
    """Compute the version that will be published.

    PyPI rejects local version identifiers, so they are always stripped here
    regardless of dev_release mode.
    """
    cleaned = version.without_local() if version.local is not None else version
    if dev_release:
        if cleaned.is_dev:
            return cleaned
        msg = f"Cannot do a dev release from non-dev version: {version.raw}"
        raise ValueError(msg)
    return cleaned.without_dev() if cleaned.is_dev else cleaned


def compute_next_version(version: Version, *, dev_release: bool = False) -> Version:
    """Compute the post-release dev version."""
    if dev_release:
        if version.is_dev:
            assert version.dev_number is not None
            return version.with_dev(version.dev_number + 1)
        msg = f"Cannot compute next dev version from non-dev version: {version.raw}"
        raise ValueError(msg)

    # Pre-release: advance within the same kind.
    if version.pre_kind is not None:
        assert version.pre_number is not None
        return Version.build(
            version.base,
            pre_kind=version.pre_kind,
            pre_number=version.pre_number + 1,
            dev_number=0,
        )
    # Post-release: advance post counter.
    if version.post_number is not None:
        return Version.build(
            version.base,
            post_number=version.post_number + 1,
            dev_number=0,
        )
    # Stable: advance patch.
    return Version.build(
        f"{version.major}.{version.minor}.{version.patch + 1}", dev_number=0
    )


def compute_bumped_version(version: Version, bump_kind: BumpKind) -> Version:
    """Compute the version that results from a bump."""
    if version.local is not None:
        msg = (
            f"Cannot bump version with local segment: {version.raw}. "
            "Strip the local segment first (set the version explicitly)."
        )
        raise ValueError(msg)
    match bump_kind:
        case BumpKind.MAJOR:
            return Version.build(f"{version.major + 1}.0.0", dev_number=0)
        case BumpKind.MINOR:
            return Version.build(f"{version.major}.{version.minor + 1}.0", dev_number=0)
        case BumpKind.PATCH:
            return Version.build(
                f"{version.major}.{version.minor}.{version.patch + 1}", dev_number=0
            )
        case BumpKind.STABLE:
            # Strip dev/pre suffix; keep post number if present.
            if version.post_number is not None:
                return Version.build(version.base, post_number=version.post_number)
            return Version.build(version.base)
        case BumpKind.DEV:
            if version.dev_number is not None:
                return version.with_dev(version.dev_number + 1)
            return version.with_dev(0)
        case BumpKind.POST:
            # POST only valid on stable/post-release versions.
            if version.pre_kind is not None:
                msg = f"Cannot bump post from pre-release: {version.raw}"
                raise ValueError(msg)
            if version.post_number is not None:
                return Version.build(
                    version.base, post_number=version.post_number + 1, dev_number=0
                )
            if version.is_dev:
                msg = f"Cannot bump post from dev version: {version.raw}"
                raise ValueError(msg)
            return Version.build(version.base, post_number=0, dev_number=0)
        case BumpKind.ALPHA:
            return _bump_pre(version, "a")
        case BumpKind.BETA:
            return _bump_pre(version, "b")
        case BumpKind.RC:
            return _bump_pre(version, "rc")
        case BumpKind.RELEASE:
            # Strip only the .devN suffix. Pre-release and post suffixes
            # carry through unchanged so a pre-release dev version
            # (1.0.0a0.dev0) resolves to its release form (1.0.0a0).
            return compute_release_version(version)
        case BumpKind.AUTO:
            return _auto_bump(version)


# Pre-release rank. Regressions (e.g. rc -> a) are forbidden.
_PRE_ORDER = {"a": 0, "b": 1, "rc": 2}


def _bump_pre(version: Version, target_kind: str) -> Version:
    if version.post_number is not None:
        msg = f"Cannot bump {target_kind} from post-release: {version.raw}"
        raise ValueError(msg)

    current_kind = version.pre_kind
    if current_kind is not None:
        current_rank = _PRE_ORDER.get(current_kind, -1)
        target_rank = _PRE_ORDER[target_kind]
        if target_rank < current_rank:
            msg = f"Cannot go from {current_kind} to {target_kind}: {version.raw}"
            raise ValueError(msg)
        if target_rank == current_rank:
            # Same kind: advance the pre-number. dev_number=0 puts the new
            # version into the dev cycle for the next release (matches the
            # rest of the bump flow, where CI strips dev on release).
            assert version.pre_number is not None
            return Version.build(
                version.base,
                pre_kind=target_kind,
                pre_number=version.pre_number + 1,
                dev_number=0,
            )
        # Higher kind: reset pre-number to 0.
        return Version.build(
            version.base, pre_kind=target_kind, pre_number=0, dev_number=0
        )

    # No existing pre-release: enter the cycle at <kind>0.dev0.
    return Version.build(version.base, pre_kind=target_kind, pre_number=0, dev_number=0)


def _auto_bump(version: Version) -> Version:
    """Increment the last section's number in place.

    dev suffix present: increment dev number (1.0.0a2.dev0 -> 1.0.0a2.dev1)
    post release:       increment post number (1.0.0.post1 -> 1.0.0.post2)
    pre-release:        increment pre number  (1.0.0a2 -> 1.0.0a3)
    clean stable:       increment patch        (1.0.0 -> 1.0.1)
    """
    if version.is_dev:
        assert version.dev_number is not None
        return version.with_dev(version.dev_number + 1)
    if version.post_number is not None:
        return Version.build(version.base, post_number=version.post_number + 1)
    if version.pre_kind is not None:
        assert version.pre_number is not None
        return Version.build(
            version.base, pre_kind=version.pre_kind, pre_number=version.pre_number + 1
        )
    return Version.build(f"{version.major}.{version.minor}.{version.patch + 1}")


def compute_dependency_pins(
    new_versions: dict[str, Version],
    all_packages: dict[str, Package],
) -> list[Pin]:
    """Compute dependency pins for packages whose deps are being bumped.

    A pin is emitted only when the dependent's existing specifier does NOT
    already accept the new version's stripped-dev form. This is the gate
    that prevents a patch bump (e.g. 1.2.0 -> 1.2.1) from rewriting every
    dependent's pyproject just to tighten its lower bound. A minor or
    major bump that lands outside the existing range emits a pin and so
    triggers a file change that change detection will pick up in the
    same release cycle.

    The lower bound is the stripped-dev form (compute_release_version),
    not the raw version. The user-driven `uvr version --bump minor` flow
    produces X.Y.0.dev0; the pin must reference X.Y.0 (the eventual
    release) so consumers can install once the release lands. The bump
    and release are expected to be coordinated in one cycle, so the dev
    intermediary never goes to PyPI alone.

    Build-system.requires entries are pinned the same way so a workspace
    package that build-depends on a sibling stays consistent.
    """
    pins: list[Pin] = []

    for pkg in all_packages.values():
        pkg_pins: dict[str, str] = {}
        # Iterate Dependency objects (not just names) so we can consult
        # the existing specifier. Runtime and build entries share one
        # dict keyed by name, so a dep listed in both collapses to a
        # single entry.
        for dep in (*pkg.dependencies, *pkg.build_dependencies):
            if dep.name not in new_versions:
                continue
            # Use the eventual release form (strip dev). The pin will
            # only become installable once the release happens, but
            # bump and release are coordinated in one cycle.
            nv = compute_release_version(new_versions[dep.name])
            # If the existing specifier already accepts the new version,
            # the pyproject does not need to move and the dependent stays
            # clean for change detection.
            if dep.satisfied_by(nv.raw):
                continue
            lower = nv.raw
            upper = f"{nv.major}.{nv.minor + 1}.0"
            pkg_pins[dep.name] = f"{dep.name}>={lower},<{upper}"
        if pkg_pins:
            pins.append(Pin(package_path=pkg.path, pins=pkg_pins))

    return pins
