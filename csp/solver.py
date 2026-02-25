#!/usr/bin/env python3
from csp_templates import Constraint, BooleanCSP
from typing import List, Optional


class Solver:
    """
    Class for solving BooleanCSP.

    Implements:
    - forward_check
    - solve
    - infer_var
    """

    def forward_check(self, csp: BooleanCSP) -> Optional[List[int]]:
        """
        Perform forward checking on any unchecked constraints in the given CSP.
        Return a list of variables (if any) whose values were inferred.
        If a contradiction is found, return None.
        """
        # Your implementation goes here.
        inferred: List[int] = []
        while csp.unchecked:
            c = csp.unchecked.popleft()
            true_vars = [v for v in c.vars if csp.value[v] is True]
            false_vars = [v for v in c.vars if csp.value[v] is False]
            unknown_vars = [v for v in c.vars if csp.value[v] is None]

            known_true = len(true_vars)
            needed_true = c.count - known_true
            remaining = len(unknown_vars)

            # Contradiction: too many True already, or can't reach required count
            if needed_true < 0 or needed_true > remaining:
                csp.reset(inferred)
                return None

            # Infer new variable values
            if needed_true == 0:
                # All unknowns must be False
                for v in unknown_vars:
                    if csp.value[v] is None:
                        csp.set(v, False)
                        inferred.append(v)
            elif needed_true == remaining:
                # All unknowns must be True
                for v in unknown_vars:
                    if csp.value[v] is None:
                        csp.set(v, True)
                        inferred.append(v)

        return inferred

    
    # Helper: recursive backtracking
    def _backtrack(self, csp: BooleanCSP) -> bool:
        # If all constrained variables are assigned, solution found
        unassigned = [
            v for v in range(csp.num_vars)
            if csp.value[v] is None and len(csp.var_constraints[v]) > 0
        ]
        if not unassigned:
            return True

        # Select variable with maximum degree
        var = max(unassigned, key=lambda v: len(csp.var_constraints[v]))

        for val in [True, False]:
            # Save state
            saved_values = csp.value[:]
            saved_unchecked = list(csp.unchecked)

            csp.set(var, val)
            inferred = self.forward_check(csp)

            if inferred is not None:
                if self._backtrack(csp):
                    return True

            # Restore state on backtrack
            csp.value = saved_values
            csp.unchecked.clear()
            csp.unchecked.extend(saved_unchecked)

        return False

    # Public backtracking solver
    def solve(self, csp: BooleanCSP) -> Optional[List[int]]:
        """
        Find a solution to the given CSP using backtracking.
        The solution will not include values for variables
        that do not belong to any constraints.
        Return a list of variables whose values were inferred.
        If no solution is found, return None.
        """
        # Your implementation goes here.
        inferred = self.forward_check(csp)
        if inferred is None:
            return None

        saved_values = csp.value[:]
        saved_unchecked = list(csp.unchecked)

        if self._backtrack(csp):
            # Return all vars that have values
            return [v for v in range(csp.num_vars) if csp.value[v] is not None]

        # Restore if unsolved
        csp.value = saved_values
        csp.unchecked.clear()
        csp.unchecked.extend(saved_unchecked)
        return None

    # -----------------------------
    # Proof-by-contradiction inference
    # -----------------------------
    def infer_var(self, csp: BooleanCSP) -> int:
        """
        Infer a value for a single variable
        if possible using a proof by contradiction.
        If any variable is inferred, return it; otherwise return -1.
        """
        # Your implementation goes here.
        vars_to_try = sorted(
            [v for v in range(csp.num_vars)
             if csp.value[v] is None and len(csp.var_constraints[v]) > 0],
            key=lambda v: len(csp.var_constraints[v]),
            reverse=True,
        )

        for var in vars_to_try:
            # Save base state
            base_values = csp.value[:]
            base_unchecked = list(csp.unchecked)

            # Try var=True
            csp.set(var, True)
            result_true = self.solve(csp)
            csp.value = base_values[:]
            csp.unchecked.clear()
            csp.unchecked.extend(base_unchecked)

            if result_true is None:
                # True causes contradiction  must be False
                csp.set(var, False)
                return var

            # Try var=False
            csp.set(var, False)
            result_false = self.solve(csp)
            csp.value = base_values[:]
            csp.unchecked.clear()
            csp.unchecked.extend(base_unchecked)

            if result_false is None:
                # False causes contradiction  must be True
                csp.set(var, True)
                return var

        return -1
