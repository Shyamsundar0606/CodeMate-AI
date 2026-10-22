"""Non-executing admission requirements. No runtime report or environment override."""

REQUIREMENTS = (
    (
        "worker_identity",
        "not_implemented",
        "Restricted worker identity",
        "A separate identity with least-privilege job access has not been provisioned or verified.",
    ),
    (
        "launcher_boundary",
        "not_implemented",
        "Trusted launcher separation",
        "No authenticated narrow launcher exists outside the API and credential-bearing AI worker.",
    ),
    (
        "image_provenance",
        "unverified",
        "Approved image provenance",
        "A pinned local image and fixture report do not independently approve upstream provenance.",
    ),
    (
        "hostile_isolation",
        "unverified",
        "Dedicated hostile-code isolation",
        "The shared Docker Desktop engine has not established the required host and VM boundary.",
    ),
    (
        "durable_recovery",
        "not_implemented",
        "Durable execution recovery",
        "Job leases, fencing, uncertain-outcome reconciliation "
        "and orphan recovery are not implemented.",
    ),
    (
        "fixture_integration",
        "not_implemented",
        "Approved patch integration",
        "No approved-patch execution through a restricted worker "
        "and persisted results has been verified.",
    ),
)


def readiness():
    # Return new values: callers cannot mutate a global approval or enable a runner.
    return {
        "policy_version": "m10-readiness-v1",
        "state": "blocked",
        "checks": [
            {"id": key, "status": status, "label": label, "reason": reason}
            for key, status, label, reason in REQUIREMENTS
        ],
    }
