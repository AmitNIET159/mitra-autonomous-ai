"""Monitoring Engine foundation interface."""
from app.models.contracts import ExecutionResult, Outcome


class MonitoringEngine:
    """Foundational interface for post-execution impact monitoring."""

    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode

    def measure_outcome(self, execution: ExecutionResult) -> Outcome:
        """Foundational interface placeholder for outcome measurement."""
        return Outcome(
            execution_id=execution.execution_id,
            metric_name="merchant_gmv_lift_percentage",
            baseline_value=10000.0,
            observed_value=11450.0,
            delta_percentage=14.5,
            is_positive=True,
            simulated=self.simulation_mode,
        )
