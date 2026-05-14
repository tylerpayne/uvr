# Replace Cascade Detection With Conditional Pin Updates

* Status: accepted
* Date: 2026-05-14

## Context and Problem Statement

`provide_changed_packages` propagated dirtiness through every reverse-dependency edge. If package A changed (even a single file edit), every workspace package depending on A was marked `"dependency changed"` and pulled into the release plan. The cascade fired regardless of whether A's new version was actually incompatible with the dependent's pin range, so patch-level releases produced cross-package release bursts that were not semantically necessary.

In parallel, `compute_dependency_pins` unconditionally rewrote pins for any workspace dep in the bumped set, tightening lower bounds even when the existing specifier already accepted the new version. And the dev-skip in that function (skipping pins when the new version was dev) meant `uvr version --bump minor` (which produces `X.(Y+1).0.dev0`) never emitted pin updates at all, leaving the cascade as the only mechanism to keep dependents in sync.

How should the release planner decide that a dependent needs to re-release?

## Decision Drivers

* The cascade often caused unnecessary releases. A patch-level file edit in A shouldn't force B, C, D to ship.
* `Dependency.satisfied_by` existed but had no callers. The pin/dep relationship was the obvious gate but nothing consulted it.
* The user-facing workflow is two commands: `uvr version --bump <axis>` then `uvr release`. The bump command should be the place where cross-package coordination happens; `uvr release` should publish whatever has file changes.
* Pin updates need to land in the same release cycle as the bump that caused them. A two-cycle gap leaves consumers seeing a published A at a new minor while B is still pinned to the old range.

## Considered Options

* Keep unconditional cascade (status quo).
* Conditional cascade in `_propagate_dirtiness`: propagate only when the dirty package's new release version doesn't satisfy the dependent's specifier.
* Drop the cascade entirely; make `compute_dependency_pins` conditional so pin rewrites during `uvr version --bump` produce file changes in dependents that file-based detection picks up on the same `uvr release`.

## Decision Outcome

Chosen option: drop the cascade and make pin emission conditional.

`provide_changed_packages` is now file-only. `_propagate_dirtiness` and `_POST_RELEASE_STATES` are deleted. `compute_dependency_pins` gates emission on `Dependency.satisfied_by(stripped_release_form)`: if the dependent's current specifier already accepts the new version's release form, no pin is written and no file changes. The lower bound is the stripped-dev form (`compute_release_version(nv)`) so a `--bump minor` that produces `0.2.0.dev0` emits a pin referencing `0.2.0`, the version that will actually be published.

The user-facing workflow:

* `uvr release` directly: patch-level releases. The bump phase sets each released package to `X.Y.(Z+1).dev0`. Next release strips dev to `X.Y.(Z+1)`. Existing pins of the form `>=X.Y.0,<X.(Y+1).0` already accept patch increments, so nothing else moves.
* `uvr version --bump minor [packages]` then `uvr release`: minor or major releases. The bump command sets target versions, and the conditional pin emitter rewrites every dependent whose existing pin no longer accepts the new release form. Those rewrites are commits inside dependents' package directories, so the subsequent `uvr release` sees both the originally bumped packages and the dependents as file-changed and releases everything together.

`ReleaseDependencyPins` switched from `BumpVersions` (next-dev like `0.2.1.dev0`) to `ReleaseVersions` (the just-published form like `0.2.0`). Under the new pin lower-bound semantics, feeding next-dev versions would have pinned consumers at versions that didn't exist yet; release-form versions stay consistent and the conditional gate makes this a no-op in the common case.

### Positive Consequences

* Patch-level releases no longer ripple across the workspace.
* `uvr version --bump` is the single place where cross-package version coordination is decided. The release command is purely file-based.
* `Dependency.satisfied_by` now has a real caller; the pin/dep relationship drives planning.
* Cascade decisions are visible in git as pin commits, not implicit in the planner.

### Negative Consequences

* `uvr version --bump minor` followed in isolation by publishing only one package would leave consumers seeing a pin pointing at an unreleased version (`pkg-b` pinned to `pkg-a>=0.2.0` when only `pkg-a` 0.1.x has been published). Bump and release are now required to be coordinated in one cycle. The previous dev-skip rule made this impossible to express; the new design accepts it as the contract.
* Cascade behavior depends on dependents declaring upper bounds in their specifiers. A bare `pkg-a` or unbounded `pkg-a>=1.0.0` is always satisfied and won't propagate. This matches semver intent but is a behavior change for workspaces that previously relied on file-based cascading.
* The `_POST_RELEASE_STATES` fast-path is gone. Its specific protection (post-releases don't cascade) is subsumed by the conditional rule for typical pin shapes but isn't a hard guarantee for exotic specifiers.

## Pros and Cons of the Options

### Keep unconditional cascade

* Good, because the release planner can keep dependents in sync without any pin discipline on the dependent side.
* Bad, because patch bumps cause unnecessary cross-package releases.
* Bad, because cascade decisions are implicit in the planner instead of visible in commits.
* Bad, because `Dependency.satisfied_by` stays dead code.

### Conditional cascade in `_propagate_dirtiness`

* Good, because patch bumps stop cascading.
* Good, because file-based detection plus a runtime version check covers the cases.
* Bad, because cascade logic and pin update logic both consult the same gate from different sites, duplicating intent.
* Bad, because cascade still happens at planner runtime, invisible in git history.
* Bad, because the cascade rule and the pin rule could drift apart over time.

### Drop cascade, conditional pin emission (chosen)

* Good, because cross-package decisions are an explicit user action (`uvr version --bump`) with a visible commit, not implicit planner behavior.
* Good, because `uvr release` semantics collapse to "publish whatever has file changes."
* Good, because the same `Dependency.satisfied_by` gate handles both "do we cascade?" and "do we write a new pin?" at the single point where the question arises.
* Bad, because the bump/release coordination contract is now load-bearing; running them out of order can publish broken pins.
* Bad, because dependents must declare upper bounds for the cascade to fire meaningfully.

## Links

* Refined by [ADR-0001](0001-use-plan-execute-architecture-for-releases.md)
* Refines [ADR-0003](0003-move-dependency-pinning-to-local-planning.md)
* Refines [ADR-0017](0017-unify-version-management-under-single-command.md)
