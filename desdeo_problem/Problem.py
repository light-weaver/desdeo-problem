"""Here various classes are defined that represent multiobjective optimization
problems.

"""

import logging
import logging.config
from abc import ABC, abstractmethod
from os import path
from typing import List, Optional, Tuple, Union, Dict, NamedTuple
# , TypedDict coming in py3.8
from functools import reduce
from operator import iadd

import numpy as np

from desdeo_problem.Constraint import ScalarConstraint
from desdeo_problem.Objective import ScalarObjective, VectorObjective
from desdeo_problem.Variable import Variable

log_conf_path = path.join(path.dirname(path.abspath(__file__)), "./logger.cfg")
logging.config.fileConfig(fname=log_conf_path, disable_existing_loggers=False)
logger = logging.getLogger(__file__)
# To prevent unexpected outputs in ipython console
logging.getLogger("parso.python.diff").disabled = True
logging.getLogger("parso.cache").disabled = True
logging.getLogger("parso.cache.pickle").disabled = True


class ProblemError(Exception):
    """Raised when an error related to the Problem class is encountered.

    """
# TODO consider replacing namedtuple with attr.s for validation purposes.


class EvaluationResults(NamedTuple):
    """The return object of <problem>.evaluate methods.

    Attributes:
        objectives (np.ndarray): The objective function values for each input
            vector.
        fitness (np.ndarray): Equal to objective values if objective is to be
            minimized. Multiplied by (-1) if objective to be maximized.
        constraints (Union[None, np.ndarray]): The constraint values of the
            problem corresponding each input vector.
        uncertainity (Union[None, np.ndarray]): The uncertainity in the
            objective values.

    """
    objectives: np.ndarray
    fitness: np.ndarray
    constraints: Union[None, np.ndarray] = None
    uncertainity: Union[None, np.ndarray] = None


class ProblemBase(ABC):
    """The base class from which every other class representing a problem should
    derive.

    """

    def __init__(self):
        self.__nadir: np.ndarray = None
        self.__ideal: np.ndarray = None
        self.__n_of_objectives: int = 0
        self.__n_of_variables: int = 0
        self.__decision_vectors: np.ndarray = None
        self.__objective_vectors: np.ndarray = None

    @property
    def nadir(self) -> np.ndarray:
        return self.__nadir

    @nadir.setter
    def nadir(self, val: np.ndarray):
        self.__nadir = val

    @property
    def ideal(self) -> np.ndarray:
        return self.__ideal

    @ideal.setter
    def ideal(self, val: np.ndarray):
        self.__ideal = val

    @property
    def n_of_objectives(self) -> int:
        return self.__n_of_objectives

    @n_of_objectives.setter
    def n_of_objectives(self, val: int):
        self.__n_of_objectives = val

    @property
    def n_of_variables(self) -> int:
        return self.__n_of_variables

    @n_of_variables.setter
    def n_of_variables(self, val: int):
        self.__n_of_variables = val

    @property
    def decision_vectors(self) -> np.ndarray:
        return self.__decision_vectors

    @decision_vectors.setter
    def decision_vectors(self, val: np.ndarray):
        self.__decision_vectors = val

    @property
    def objective_vectors(self) -> np.ndarray:
        return self.__objective_vectors

    @objective_vectors.setter
    def objective_vectors(self, val: np.ndarray):
        self.__objective_vectors = val

    @abstractmethod
    def get_variable_bounds(self) -> Union[None, np.ndarray]:
        pass

    @abstractmethod
    def evaluate(
        self, decision_vectors: np.ndarray
    ) -> Dict:
        """Evaluates the problem using an ensemble of input vectors.

        Args:
            decision_vectors (np.ndarray): An array of decision variable
            input vectors.

        Returns:
            (Dict): Dict with the following keys:
                'objectives' (np.ndarray): The objective function values for each input
                    vector.
                'constraints' (Union[np.ndarray, None]): The constraint values of the
                    problem corresponding each input vector.
                'fitness' (np.ndarray): Equal to objective values if objective is to be
                    minimized. Multiplied by (-1) if objective to be maximized.
                'uncertainity' (Union[np.ndarray, None]): The uncertainity in the
                    objective values.

        """
        pass

    @abstractmethod
    def evaluate_constraint_values(self) -> Optional[np.ndarray]:
        """Evaluate just the constraint function values using the attributes
        decision_vectors and objective_vectors

        Note:
            Currently not supported by ScalarMOProblem

        """
        pass


class ScalarMOProblem(ProblemBase):
    """A multiobjective optimization problem with user defined objective funcitons,
    constraints and variables. The objectives each return a single scalar.

    Args:
        objectives (List[ScalarObjective]): A list containing the objectives of
        the problem.
        variables (List[Variable]): A list containing the variables of the
        problem.
        constraints (List[ScalarConstraint]): A list containing the
        constraints of the problem. If no constraints exist, None may
        be supllied as the value.
        nadir (Optional[np.ndarray]): The nadir point of the problem.
        ideal (Optional[np.ndarray]): The ideal point of the problem.

    Attributes:
        n_of_objectives (int): The number of objectives in the problem.
        n_of_variables (int): The number of variables in the problem.
        n_of_constraints (int): The number of constraints in the problem.
        nadir (np.ndarray): The nadir point of the problem.
        ideal (np.ndarray): The ideal point of the problem.
        objectives (List[ScalarObjective]): A list containing the objectives of
        the problem.
        constraints (List[ScalarConstraint]): A list conatining the constraints
        of the problem.

    Raises:
        ProblemError: Ill formed nadir and/or ideal vectors are supplied.

    """

    def __init__(
        self,
        objectives: List[ScalarObjective],
        variables: List[Variable],
        constraints: List[ScalarConstraint],
        nadir: Optional[np.ndarray] = None,
        ideal: Optional[np.ndarray] = None,
    ) -> None:
        super().__init__()
        self.__objectives: List[ScalarObjective] = objectives
        self.__variables: List[Variable] = variables
        self.__constraints: List[ScalarConstraint] = constraints

        self.__n_of_objectives: int = len(self.objectives)
        self.__n_of_variables: int = len(self.variables)

        if self.constraints is not None:
            self.__n_of_constraints: int = len(self.constraints)
        else:
            self.__n_of_constraints = 0

        # Nadir vector must be the same size as the number of objectives
        if nadir is not None:
            if len(nadir) != self.n_of_objectives:
                msg = (
                    "The length of the nadir vector does not match the"
                    "number of objectives: Length nadir {}, number of "
                    "objectives {}."
                ).format(len(nadir), self.n_of_objectives)
                logger.error(msg)
                raise ProblemError(msg)

        # Ideal vector must be the same size as the number of objectives
        if ideal is not None:
            if len(ideal) != self.n_of_objectives:
                msg = (
                    "The length of the ideal vector does not match the"
                    "number of objectives: Length ideal {}, number of "
                    "objectives {}."
                ).format(len(ideal), self.n_of_objectives)
                logger.error(msg)
                raise ProblemError(msg)

        # Nadir and ideal vectors must match in size
        if nadir is not None and ideal is not None:
            if len(nadir) != len(ideal):
                msg = (
                    "The length of the nadir and ideal point don't match:"
                    " length of nadir {}, length of ideal {}."
                ).format(len(nadir), len(ideal))
                logger.error(msg)
                raise ProblemError(msg)

        self.__nadir = nadir
        self.__ideal = ideal

    @property
    def n_of_constraints(self) -> int:
        return self.__n_of_constraints

    @n_of_constraints.setter
    def n_of_constraints(self, val: int):
        self.__n_of_constraints = val

    @property
    def objectives(self) -> List[ScalarObjective]:
        return self.__objectives

    @objectives.setter
    def objectives(self, val: List[ScalarObjective]):
        self.__objectives = val

    @property
    def variables(self) -> List[Variable]:
        return self.__variables

    @variables.setter
    def variables(self, val: List[Variable]):
        self.__variables = val

    @property
    def constraints(self) -> List[ScalarConstraint]:
        return self.__constraints

    @constraints.setter
    def constraints(self, val: List[ScalarConstraint]):
        self.__constraints = val

    @property
    def n_of_constraints(self) -> int:
        return self.__n_of_constraints

    @n_of_constraints.setter
    def n_of_constraints(self, val: int):
        self.__n_of_constraints = val

    @property
    def n_of_objectives(self) -> int:
        return self.__n_of_objectives

    @n_of_objectives.setter
    def n_of_objectives(self, val: int):
        self.__n_of_objectives = val

    @property
    def n_of_variables(self) -> int:
        return self.__n_of_variables

    @n_of_variables.setter
    def n_of_variables(self, val: int):
        self.__n_of_variables = val

    @property
    def nadir(self) -> np.ndarray:
        return self.__nadir

    @nadir.setter
    def nadir(self, val: np.ndarray):
        self.__nadir = val

    @property
    def ideal(self) -> np.ndarray:
        return self.__ideal

    @ideal.setter
    def ideal(self, val: np.ndarray):
        self.__ideal = val

    def get_variable_bounds(self) -> Union[np.ndarray, None]:
        """Return the upper and lower bounds of each decision variable present
        in the problem as a 2D numpy array. The first column corresponds to the
        lower bounds of each variable, and the second column to the upper
        bound.

        Returns:
           np.ndarray: Lower and upper bounds of each variable
           as a 2D numpy array. If undefined variables, return None instead.

        """
        if self.variables is not None:
            bounds = np.ndarray((self.n_of_variables, 2))
            for ind, var in enumerate(self.variables):
                bounds[ind] = np.array(var.get_bounds())
            return bounds
        else:
            logger.info(
                "Attempted to get variable bounds for a "
                "ScalarMOProblem with no defined variables."
            )
            return None

    def get_variable_names(self) -> List[str]:
        """Return the variable names of the variables present in the problem in
        the order they were added.

        Returns:
            List[str]: Names of the variables in the order they were added.

        """
        return [var.name for var in self.variables]

    def get_objective_names(self) -> List[str]:
        """Return the names of the objectives present in the problem in the
        order they were added.

        Returns:
            List[str]: Names of the objectives in the order they were added.

        """
        return [obj.name for obj in self.objectives]

    def get_variable_lower_bounds(self) -> np.ndarray:
        """Return the lower bounds of each variable as a list. The order of the bounds
        follows the order the variables were added to the problem.

        Returns:
            np.ndarray: An array with the lower bounds of the variables.
        """
        return np.array([var.get_bounds()[0] for var in self.variables])

    def get_variable_upper_bounds(self) -> np.ndarray:
        """Return the upper bounds of each variable as a list. The order of the bounds
        follows the order the variables were added to the problem.

        Returns:
            np.ndarray: An array with the upper bounds of the variables.
        """
        return np.array([var.get_bounds()[1] for var in self.variables])

    def evaluate(
        self, decision_vectors: np.ndarray
    ) -> EvaluationResults:
        """Evaluates the problem using an ensemble of input vectors.

        Args:
            decision_vectors (np.ndarray): An 2D array of decision variable
            input vectors. Each column represent the values of each decision
            variable.

        Returns:
            Tuple[np.ndarray, Union[None, np.ndarray]]: If constraint are
            defined, returns the objective vector values and corresponding
            constraint values. Or, if no constraints are defined, returns just
            the objective vector values with None as the constraint values.

        Raises:
            ProblemError: The decision_vectors have wrong dimensions.

        """
        # Reshape decision_vectors with single row to work with the code
        shape = np.shape(decision_vectors)
        if len(shape) == 1:
            decision_vectors = np.reshape(decision_vectors, (1, shape[0]))

        (n_rows, n_cols) = np.shape(decision_vectors)

        if n_cols != self.n_of_variables:
            msg = (
                "The length of the input vectors does not match the number "
                "of variables in the problem: Input vector length {}, "
                "number of variables {}."
            ).format(n_cols, self.n_of_variables)
            logger.error(msg)
            raise ProblemError(msg)

        objective_vectors: np.ndarray = np.ndarray(
            (n_rows, self.n_of_objectives), dtype=float
        )
        if self.n_of_constraints > 0:
            constraint_values: np.ndarray = np.ndarray(
                (n_rows, self.n_of_constraints), dtype=float
            )
        else:
            constraint_values = None

        # Calculate the objective values
        for (col_i, objective) in enumerate(self.objectives):
            objective_vectors[:, col_i] = np.array(
                list(map(objective.evaluate, decision_vectors))
            )

        # Calculate the constraint values
        if constraint_values is not None:
            for (col_i, constraint) in enumerate(self.constraints):
                constraint_values[:, col_i] = np.array(
                    list(map(constraint.evaluate, decision_vectors, objective_vectors))
                )

        return (objective_vectors, constraint_values)

    def evaluate_constraint_values(self) -> Optional[np.ndarray]:
        """Evaluate just the constraint function values using the attributes
        decision_vectors and objective_vectors

        Raises:
            NotImplementedError

        Note:
            Currently not supported by ScalarMOProblem

        """
        raise NotImplementedError("Not implemented for ScalarMOProblem")


class ScalarDataProblem(ProblemBase):
    """Defines a problem with pre-computed data representing a multiobjective
    optimization problem with scalar valued objective functions.

    Args:
        decision_vectors (np.ndarray): A 2D vector of decision_vectors. Each
        row represents a solution with the value for each decision_vectors
        defined on the columns.
        objective_vectors (np.ndarray): A 2D vector of
        objective function values. Each row represents one objective vector
        with the values for the invidual objective functions defined on the
        columns.

    Attributes:
        decision_vectors (np.ndarray): See args
        objective_vectors (np.ndarray): See args
        epsilon (float): A small floating point number to shift the bounds of
        the variables. See, get_variable_bounds
        constraints (List[ScalarConstraint]): A list of defined constraints.
        nadir (np.ndarray): The nadir point of the problem.
        ideal (np.ndarray): The ideal point of the problem.

    Note:
        It is assumed that the decision_vectors and objectives follow a direct
        one-to-one mapping, i.e., the objective values on the ith row in
        'objectives' should represent the solution of the multiobjective
        problem when evaluated with the decision_vectors on the ith row in
        'decision_vectors'.

    """

    def __init__(self, decision_vectors: np.ndarray, objective_vectors: np.ndarray):
        super().__init__()
        self.decision_vectors: np.ndarray = decision_vectors
        self.objective_vectors: np.ndarray = objective_vectors
        # epsilon is used when computing the bounds. We don't want to exclude
        # any of the solutions that contain border values.
        # See get_variable_bounds
        self.__epsilon: float = 1e-6
        # Used to indicate if a model has been built to represent the model.
        # Used in the evaluation.
        self.__model_exists: bool = False
        self.__constraints: List[ScalarConstraint] = []

        try:
            self.n_of_variables = self.decision_vectors.shape[1]
        except IndexError as e:
            msg = (
                "Check the variable dimensions. Is it a 2D array? "
                "Encountered '{}'".format(str(e))
            )
            logger.error(msg)
            raise ProblemError(msg)

        try:
            self.n_of_objectives = self.objective_vectors.shape[1]
        except IndexError as e:
            msg = (
                "Check the objective dimensions. Is it a 2D array? "
                "Encountered '{}'".format(str(e))
            )
            logger.error(msg)
            raise ProblemError(msg)

        self.nadir = np.max(self.objective_vectors, axis=0)
        self.ideal = np.min(self.objective_vectors, axis=0)

    @property
    def epsilon(self) -> float:
        return self.__epsilon

    @epsilon.setter
    def epsilon(self, val: float):
        self.__epsilon = val

    @property
    def constraints(self) -> List[ScalarConstraint]:
        return self.__constraints

    @constraints.setter
    def constraints(self, val: List[ScalarConstraint]):
        self.__constraints = val

    def get_variable_bounds(self):
        """Return the variable bounds. A small value might be added to the
        upper bounds and substracted from the lower bounds to return closed
        bounds.

        Note:
            If self.epsilon is zero, the bounds will represent an open range.

        """
        return np.stack(
            (
                np.min(self.decision_vectors, axis=0) - self.epsilon,
                np.max(self.decision_vectors, axis=0) + self.epsilon,
            ),
            axis=1,
        )

    def evaluate_constraint_values(self) -> Optional[np.ndarray]:
        """Evaluate the constraint values for each defined constraint. A
        positive value indicates that a constraint is adhered to, a negative
        value indicates a violated constraint.

        Returns:
            Optional[np.ndarray]: A 2D array with each row representing the
            constraint values for different objective vectors. One column for
            each constraint. If no constraint function are defined, returns
            None.

        """
        if len(self.constraints) == 0:
            return None

        constraint_values = np.zeros(
            (len(self.objective_vectors), len(self.constraints))
        )

        for ind, con in enumerate(self.constraints):
            constraint_values[:, ind] = con.evaluate(
                self.decision_vectors, self.objective_vectors
            )

        return constraint_values

    def evaluate(self, decision_vectors: np.ndarray) -> np.ndarray:
        """Evaluate the values of the objectives corresponding to the decision
        decision_vectors.

        Args:
            decision_vectors (np.ndarray): A 2D array with the decision
            decision_vectors to be evaluated on each row.

        Returns:
            nd.ndarray: A 2D array with the objective values corresponding to
            each decision vectors on the rows.

        Note:
            At the moment, this function just maps the given decision
            decision_vectors to the closest decision variable present (using an
            L2 distance) in the problem and returns the corresponsing objective
            vector.

            """
        if not self.__model_exists:
            logger.warning(
                "Warning: Approximating the closest known point in "
                "a data based problem. Consider building a model "
                "first (NOT IMPLEMENTED)"
            )
            idx = np.unravel_index(
                np.linalg.norm(
                    self.decision_vectors - decision_vectors, axis=1
                ).argmin(),
                self.objective_vectors.shape,
                order="F",
            )[0]

        else:
            msg = "Models not implemented yet for data based problems."
            logger.error(msg)
            raise NotImplementedError(msg)

        return (self.objective_vectors[idx],)


class MOProblem(ProblemBase):
    """A multiobjective optimization problem with user defined objective funcitons,
    constraints and variables.


    Args:
        objectives (List[Union[ScalarObjective, VectorObjective]]): A list containing
            the objectives of the problem.
        variables (List[Variable]): A list containing the variables of the problem.
        constraints (List[ScalarConstraint]): A list of the constraints of the problem.
        nadir (Optional[np.ndarray], optional): Nadir point of the problem.
            Defaults to None.
        ideal (Optional[np.ndarray], optional): Ideal point of the problem.
            Defaults to None.

    Raises:
        ProblemError: If ideal or nadir vectors are not the same size as number of
            objectives.

    Returns:
        [type]: [description]
    """

    def __init__(
        self,
        objectives: List[Union[ScalarObjective, VectorObjective]],
        variables: List[Variable],
        constraints: List[ScalarConstraint],
        nadir: Optional[np.ndarray] = None,
        ideal: Optional[np.ndarray] = None,
    ):
        super().__init__()
        self.__objectives: List[Union[ScalarObjective, VectorObjective]] = objectives
        self.__variables: List[Variable] = variables
        self.__constraints: List[ScalarConstraint] = constraints
        self.__n_of_variables: int = len(self.variables)
        self.__n_of_objectives: int = sum(map(number_of_objectives, self.__objectives))
        if self.constraints is not None:
            self.__n_of_constraints: int = len(self.constraints)
        else:
            self.__n_of_constraints = 0

        # Nadir vector must be the same size as the number of objectives
        if nadir is not None:
            if len(nadir) != self.n_of_objectives:
                msg = (
                    "The length of the nadir vector does not match the"
                    "number of objectives: Length nadir {}, number of "
                    "objectives {}."
                ).format(len(nadir), self.n_of_objectives)
                logger.error(msg)
                raise ProblemError(msg)

        # Ideal vector must be the same size as the number of objectives
        if ideal is not None:
            if len(ideal) != self.n_of_objectives:
                msg = (
                    "The length of the ideal vector does not match the"
                    "number of objectives: Length ideal {}, number of "
                    "objectives {}."
                ).format(len(ideal), self.n_of_objectives)
                logger.error(msg)
                raise ProblemError(msg)

        self.__nadir = nadir
        self.__ideal = ideal

    @property
    def n_of_constraints(self) -> int:
        return self.__n_of_constraints

    @n_of_constraints.setter
    def n_of_constraints(self, val: int):
        self.__n_of_constraints = val

    @property
    def objectives(self) -> List[ScalarObjective]:
        return self.__objectives

    @objectives.setter
    def objectives(self, val: List[ScalarObjective]):
        self.__objectives = val

    @property
    def variables(self) -> List[Variable]:
        return self.__variables

    @variables.setter
    def variables(self, val: List[Variable]):
        self.__variables = val

    @property
    def constraints(self) -> List[ScalarConstraint]:
        return self.__constraints

    @constraints.setter
    def constraints(self, val: List[ScalarConstraint]):
        self.__constraints = val

    @property
    def n_of_objectives(self) -> int:
        return self.__n_of_objectives

    @n_of_objectives.setter
    def n_of_objectives(self, val: int):
        self.__n_of_objectives = val

    @property
    def n_of_variables(self) -> int:
        return self.__n_of_variables

    @n_of_variables.setter
    def n_of_variables(self, val: int):
        self.__n_of_variables = val

    @property
    def nadir(self) -> np.ndarray:
        return self.__nadir

    @nadir.setter
    def nadir(self, val: np.ndarray):
        self.__nadir = val

    @property
    def ideal(self) -> np.ndarray:
        return self.__ideal

    @ideal.setter
    def ideal(self, val: np.ndarray):
        self.__ideal = val

    def get_variable_bounds(self) -> Union[np.ndarray, None]:
        """Return the upper and lower bounds of each decision variable present
        in the problem as a 2D numpy array. The first column corresponds to the
        lower bounds of each variable, and the second column to the upper
        bound.

        Returns:
           np.ndarray: Lower and upper bounds of each variable
           as a 2D numpy array. If undefined variables, return None instead.

        """
        if self.variables is not None:
            bounds = np.ndarray((self.n_of_variables, 2))
            for ind, var in enumerate(self.variables):
                bounds[ind] = np.array(var.get_bounds())
            return bounds
        else:
            logger.info(
                "Attempted to get variable bounds for a "
                "MOProblem with no defined variables."
            )
            return None

    def get_variable_names(self) -> List[str]:
        """Return the variable names of the variables present in the problem in
        the order they were added.

        Returns:
            List[str]: Names of the variables in the order they were added.

        """
        return [var.name for var in self.variables]

    def get_objective_names(self) -> List[str]:
        """Return the names of the objectives present in the problem in the
        order they were added.

        Returns:
            List[str]: Names of the objectives in the order they were added.

        """
        obj_list = [list(obj.name) for obj in self.objectives]
        return reduce(iadd, obj_list, [])

    def get_variable_lower_bounds(self) -> np.ndarray:
        """Return the lower bounds of each variable as a list. The order of the bounds
        follows the order the variables were added to the problem.

        Returns:
            np.ndarray: An array with the lower bounds of the variables.
        """
        return np.array([var.get_bounds()[0] for var in self.variables])

    def get_variable_upper_bounds(self) -> np.ndarray:
        """Return the upper bounds of each variable as a list. The order of the bounds
        follows the order the variables were added to the problem.

        Returns:
            np.ndarray: An array with the upper bounds of the variables.
        """
        return np.array([var.get_bounds()[1] for var in self.variables])

    def evaluate(
        self, decision_vectors: np.ndarray
    ) -> EvaluationResults:
        """Evaluates the problem using an ensemble of input vectors.

        Args:
            decision_vectors (np.ndarray): An 2D array of decision variable
            input vectors. Each column represent the values of each decision
            variable.

        Returns:
            Tuple[np.ndarray, Union[None, np.ndarray]]: If constraint are
            defined, returns the objective vector values and corresponding
            constraint values. Or, if no constraints are defined, returns just
            the objective vector values with None as the constraint values.

        Raises:
            ProblemError: The decision_vectors have wrong dimensions.
            ValueError: If decision_vectors violate the lower or upper bounds.

        """
        # Reshape decision_vectors with single row to work with the code
        shape = np.shape(decision_vectors)
        if len(shape) == 1:
            decision_vectors = np.reshape(decision_vectors, (1, shape[0]))

        # Checking bounds
        if np.any(self.get_variable_lower_bounds() > decision_vectors):
            raise ValueError("Some decision variable values violate lower bounds")
        if np.any(self.get_variable_upper_bounds() < decision_vectors):
            raise ValueError("Some decision variable values violate upper bounds")

        (n_rows, n_cols) = np.shape(decision_vectors)

        if n_cols != self.n_of_variables:
            msg = (
                "The length of the input vectors does not match the number "
                "of variables in the problem: Input vector length {}, "
                "number of variables {}."
            ).format(n_cols, self.n_of_variables)
            logger.error(msg)
            raise ProblemError(msg)

        objective_vectors: np.ndarray = np.ndarray(
            (n_rows, self.n_of_objectives), dtype=float
        )
        if self.n_of_constraints > 0:
            constraint_values: np.ndarray = np.ndarray(
                (n_rows, self.n_of_constraints), dtype=float
            )
        else:
            constraint_values = None

        # Calculate the objective values
        obj_column = 0
        for objective in self.objectives:
            elem_in_curr_obj = number_of_objectives(objective)
            if elem_in_curr_obj == 1:
                objective_vectors[:, obj_column] = np.array(
                    list(map(objective.evaluate, decision_vectors))
                )
            elif elem_in_curr_obj > 1:
                objective_vectors[
                    :, obj_column : obj_column + elem_in_curr_obj
                ] = np.array(list(map(objective.evaluate, decision_vectors)))
            obj_column = obj_column + elem_in_curr_obj

        # Calculate the constraint values
        if constraint_values is not None:
            for (col_i, constraint) in enumerate(self.constraints):
                constraint_values[:, col_i] = np.array(
                    list(map(constraint.evaluate, decision_vectors, objective_vectors))
                )

        return (objective_vectors, constraint_values)

    def evaluate_constraint_values(self) -> Optional[np.ndarray]:
        """Evaluate just the constraint function values using the attributes
        decision_vectors and objective_vectors

        Raises:
            NotImplementedError

        Note:
            Currently not supported by ScalarMOProblem

        """
        raise NotImplementedError("Not implemented for ScalarMOProblem")


def number_of_objectives(obj_instance: Union[ScalarObjective, VectorObjective]) -> int:
    """Return the number of objectives in the given obj_instance.

    Args:
        obj_instance (Union[ScalarObjective, VectorObjective]): An instance of one of
            the objective classes

    Raises:
        ProblemError: Raised when obj_instance is not an instance of the supported
            classes

    Returns:
        int: Number of objectives in obj_instance
    """
    if isinstance(obj_instance, ScalarObjective):
        return 1
    elif isinstance(obj_instance, VectorObjective):
        return obj_instance.n_of_objectives
    else:
        msg = "Supported objective types: ScalarObjective and VectorObjective"
        raise ProblemError(msg)
