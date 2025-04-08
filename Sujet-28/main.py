from ortools.sat.python import cp_model
import time
from typing import List, Dict, Callable, Optional, Tuple, Any
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("allocation_algo.log"), logging.StreamHandler()],
)
logger = logging.getLogger("allocation_algo")


def student_project_allocation_cp_sat(
    students: List[int],
    projects: List[int],
    preferences: Dict[int, List[int]],
    project_capacities: Dict[int, int],
    constraints: Optional[List[Callable]] = None,
) -> Tuple[Optional[Dict[int, int]], float, str]:
    """
    Solves the student project allocation problem using OR-Tools CP-SAT (no supervisors).
    Returns solution, execution time, and algorithm name.
    """
    start_time = time.time()
    logger.info("Running CP-SAT algorithm...")

    model = cp_model.CpModel()

    # Create variables: assignment[student, project] = 1 if student is assigned to project.
    assignments: Dict[tuple[int, int], cp_model.IntVar] = {}
    for student in students:
        for project in projects:
            assignments[(student, project)] = model.NewBoolVar(
                f"assignment_s{student}_p{project}"
            )

    # Constraint 1: Each student is assigned to exactly one project.
    for student in students:
        model.Add(sum(assignments[(student, project)] for project in projects) == 1)

    # Constraint 2: Project capacities are respected.
    for project in projects:
        model.Add(
            sum(assignments[(student, project)] for student in students)
            <= project_capacities[project]
        )

    # Constraint 3: Only assign projects that are in the student's preferences.
    for student in students:
        preferred_projects = preferences.get(student, [])
        if preferred_projects == []:
            preferred_projects = projects
        for project in projects:
            if project not in preferred_projects:
                model.Add(assignments[(student, project)] == 0)  # Cannot be assigned.

    # Custom constraints (optional)
    if constraints:
        for constraint_function in constraints:
            constraint_function(model, students, projects, assignments)

    # Objective function: Maximize the satisfaction of student preferences
    objective_terms = []
    for student in students:
        preferred_projects = preferences.get(student, [])
        for i, project in enumerate(preferred_projects):
            priority = len(preferred_projects) - i
            objective_terms.append(
                cp_model.LinearExpr.Term(
                    assignments[(student, project)], priority * 100
                )
            )

    model.Maximize(sum(objective_terms))

    # Solve the model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    execution_time = time.time() - start_time
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        allocation: Dict[int, int] = {}
        for student in students:
            for project in projects:
                if solver.Value(assignments[(student, project)]) == 1:
                    allocation[student] = project
                    break
        logger.info(f"CP-SAT found solution in {execution_time:.4f}s")
        return allocation, execution_time, "CP-SAT"
    else:
        logger.info(f"CP-SAT failed to find solution in {execution_time:.4f}s")
        return None, execution_time, "CP-SAT"


def student_project_allocation_greedy(
    students: List[int],
    projects: List[int],
    preferences: Dict[int, List[int]],
    project_capacities: Dict[int, int],
    constraints: Optional[List[Callable]] = None,
) -> Tuple[Optional[Dict[int, int]], float, str]:
    """
    Solves the student project allocation problem using a greedy algorithm.
    Returns solution, execution time, and algorithm name.
    """
    start_time = time.time()
    logger.info("Running Greedy algorithm...")

    # Create a copy of project capacities to track remaining spots
    remaining_capacity = project_capacities.copy()
    allocation = {}

    # Sort students by preference list length (fewer options first)
    sorted_students = sorted(
        students,
        key=lambda s: len(preferences.get(s, [])) if s in preferences else float("inf"),
    )

    # Allocate projects to students
    for student in sorted_students:
        allocated = False
        student_prefs = preferences.get(student, projects.copy())

        for project in student_prefs:
            if project in remaining_capacity and remaining_capacity[project] > 0:
                allocation[student] = project
                remaining_capacity[project] -= 1
                allocated = True
                break

        if not allocated:
            # If no preferred project available, try any project with remaining capacity
            for project in projects:
                if project in remaining_capacity and remaining_capacity[project] > 0:
                    allocation[student] = project
                    remaining_capacity[project] -= 1
                    allocated = True
                    break

        if not allocated:
            # Cannot allocate this student
            execution_time = time.time() - start_time
            logger.info(f"Greedy algorithm failed to allocate student {student}")
            return None, execution_time, "Greedy"

    # Check if custom constraints are satisfied
    # Note: This is a simplified check and may not handle all constraint types
    if constraints and len(allocation) == len(students):
        for student in students:
            if student not in allocation:
                execution_time = time.time() - start_time
                logger.info("Greedy algorithm failed due to constraints")
                return None, execution_time, "Greedy"

    execution_time = time.time() - start_time
    logger.info(f"Greedy algorithm completed in {execution_time:.4f}s")
    return allocation, execution_time, "Greedy"


def student_project_allocation_random(
    students: List[int],
    projects: List[int],
    preferences: Dict[int, List[int]],
    project_capacities: Dict[int, int],
    constraints: Optional[List[Callable]] = None,
    max_iterations: int = 1000,
) -> Tuple[Optional[Dict[int, int]], float, str]:
    """
    Solves the student project allocation problem using random assignment with multiple attempts.
    Returns solution, execution time, and algorithm name.
    """
    start_time = time.time()
    logger.info("Running Random algorithm...")

    best_allocation = None
    best_score = -1

    for _ in range(max_iterations):
        # Create a copy of project capacities to track remaining spots
        remaining_capacity = project_capacities.copy()
        allocation = {}

        # Shuffle students to create randomness
        shuffled_students = students.copy()
        random.shuffle(shuffled_students)

        # Try to allocate each student
        for student in shuffled_students:
            # Get preferred projects or all projects if no preferences
            student_prefs = preferences.get(student, projects.copy())
            random.shuffle(student_prefs)  # Randomize preference order

            allocated = False
            for project in student_prefs:
                if project in remaining_capacity and remaining_capacity[project] > 0:
                    allocation[student] = project
                    remaining_capacity[project] -= 1
                    allocated = True
                    break

            if not allocated:
                # If no preferred project available, try any project with capacity
                available_projects = [
                    p for p in projects if remaining_capacity.get(p, 0) > 0
                ]
                if available_projects:
                    project = random.choice(available_projects)
                    allocation[student] = project
                    remaining_capacity[project] -= 1
                    allocated = True

            if not allocated:
                # This attempt failed
                break

        # Check if all students were allocated
        if len(allocation) == len(students):
            # Calculate score (higher is better)
            score = 0
            for student, project in allocation.items():
                if student in preferences and project in preferences[student]:
                    # Points based on preference position (higher for more preferred)
                    score += len(preferences[student]) - preferences[student].index(
                        project
                    )

            if score > best_score:
                best_score = score
                best_allocation = allocation

    execution_time = time.time() - start_time
    logger.info(f"Random algorithm completed in {execution_time:.4f}s")
    return best_allocation, execution_time, "Random"


def calculate_allocation_score(
    allocation: Dict[int, int], preferences: Dict[int, List[int]]
) -> float:
    """Calculate a satisfaction score for an allocation."""
    score = 0
    for student, project in allocation.items():
        if student in preferences and project in preferences[student]:
            # Points based on preference position (higher for more preferred)
            pref_index = preferences[student].index(project)
            pref_len = len(preferences[student])
            score += (pref_len - pref_index) / pref_len  # Normalize to 0-1 range
        else:
            score -= 0.5  # Penalty for allocations outside preferences
    return score


def student_project_allocation(
    students: List[int],
    projects: List[int],
    preferences: Dict[int, List[int]],
    project_capacities: Dict[int, int],
    constraints: Optional[List[Callable]] = None,
) -> Tuple[Optional[Dict[int, int]], Dict[str, Any]]:
    """
    Main function that runs multiple algorithms, benchmarks them, and returns the best solution.
    Also returns detailed benchmark information.
    """
    logger.info("Starting student project allocation...")
    logger.info(f"students: {students}")
    logger.info(f"projects: {projects}")
    logger.info(f"preferences: {preferences}")
    logger.info(f"project_capacities: {project_capacities}")
    logger.info(f"constraints: {constraints}")

    # Run all algorithms
    results = []
    benchmark_info = {}

    # CP-SAT algorithm
    cp_sat_result, cp_sat_time, cp_sat_name = student_project_allocation_cp_sat(
        students, projects, preferences, project_capacities, constraints
    )
    if cp_sat_result:
        cp_sat_score = calculate_allocation_score(cp_sat_result, preferences)
        results.append((cp_sat_result, cp_sat_time, cp_sat_score, cp_sat_name))
        logger.info(
            f"CP-SAT algorithm: Score={cp_sat_score:.4f}, Time={cp_sat_time:.4f}s"
        )
        benchmark_info["CP-SAT"] = {
            "score": cp_sat_score,
            "time": cp_sat_time,
            "solution_found": True,
        }
    else:
        logger.info(f"CP-SAT algorithm: No solution found, Time={cp_sat_time:.4f}s")
        benchmark_info["CP-SAT"] = {
            "score": None,
            "time": cp_sat_time,
            "solution_found": False,
        }

    # Greedy algorithm
    greedy_result, greedy_time, greedy_name = student_project_allocation_greedy(
        students, projects, preferences, project_capacities, constraints
    )
    if greedy_result:
        greedy_score = calculate_allocation_score(greedy_result, preferences)
        results.append((greedy_result, greedy_time, greedy_score, greedy_name))
        logger.info(
            f"Greedy algorithm: Score={greedy_score:.4f}, Time={greedy_time:.4f}s"
        )
        benchmark_info["Greedy"] = {
            "score": greedy_score,
            "time": greedy_time,
            "solution_found": True,
        }
    else:
        logger.info(f"Greedy algorithm: No solution found, Time={greedy_time:.4f}s")
        benchmark_info["Greedy"] = {
            "score": None,
            "time": greedy_time,
            "solution_found": False,
        }

    # Random algorithm
    random_result, random_time, random_name = student_project_allocation_random(
        students, projects, preferences, project_capacities, constraints
    )
    if random_result:
        random_score = calculate_allocation_score(random_result, preferences)
        results.append((random_result, random_time, random_score, random_name))
        logger.info(
            f"Random algorithm: Score={random_score:.4f}, Time={random_time:.4f}s"
        )
        benchmark_info["Random"] = {
            "score": random_score,
            "time": random_time,
            "solution_found": True,
        }
    else:
        logger.info(f"Random algorithm: No solution found, Time={random_time:.4f}s")
        benchmark_info["Random"] = {
            "score": None,
            "time": random_time,
            "solution_found": False,
        }

    # Choose the best solution based on score
    best_result = None
    if results:
        # Sort by score (higher is better)
        results.sort(key=lambda x: x[2], reverse=True)
        best_result, best_time, best_score, best_algo = results[0]
        logger.info(
            f"Best solution found by {best_algo} algorithm with score {best_score:.4f}"
        )
        logger.info(f"Allocation: {best_result}")

        # Add best algorithm info to benchmark data
        benchmark_info["best_algorithm"] = best_algo
        benchmark_info["best_score"] = best_score
    else:
        logger.info("No solution found by any algorithm")
        benchmark_info["best_algorithm"] = None
        benchmark_info["best_score"] = None

    return best_result, benchmark_info


# Example usage:
if __name__ == "__main__":
    students = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    projects = [101, 102, 103, 104, 105]

    preferences = {
        1: [101, 102, 103],
        2: [102, 104, 101],
        3: [103, 101, 104],
        4: [104, 103, 102],
        5: [101, 104, 102],
        6: [102, 101, 103],
        7: [105, 101, 102],
        8: [103, 105, 104],
        9: [104, 102, 105],
        10: [101, 103, 105],
    }

    project_capacities = {101: 2, 102: 2, 103: 1, 104: 2, 105: 2}

    def example_constraint(model, students, projects, assignments):
        # Example custom constraint 1: Student 1 and 2 cannot be on the same project
        for project in projects:
            model.Add(assignments[(1, project)] + assignments[(2, project)] <= 1)

        # Example custom constraint 2:  If student 3 is on project 101, then student 4 must be on project 102
        model.AddBoolOr([assignments[(3, 101)].Not(), assignments[(4, 102)]])

        # Example custom constraint 3: Ensure at least one of students 5, 6, or 7 is assigned to project 105
        model.Add(sum(assignments[(s, 105)] for s in [5, 6, 7]) >= 1)

    allocation, benchmark_info = student_project_allocation(
        students,
        projects,
        preferences,
        project_capacities,
        constraints=[example_constraint],  # Pass custom constraints here.
    )

    if allocation:
        for student, project in allocation.items():
            print(f"Student {student} is assigned to project {project}")
        print("Benchmark Information:", benchmark_info)
