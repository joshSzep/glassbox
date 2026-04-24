"""Shared replay failure types used across bundle loading and execution."""


class ReplayManifestDrift(RuntimeError):
    pass


class ReplayUnsupportedSession(RuntimeError):
    pass


class ReplayFailure(RuntimeError):
    pass
