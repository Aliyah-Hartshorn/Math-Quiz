"""
Math Quiz
=========

A single-file Python console application that generates randomized, timed
math questions spanning fourteen topics, from basic arithmetic through
very advanced material: Arithmetic, Number Theory, Algebra, Precalculus,
Geometry, Trigonometry, Combinatorics, Statistics, Complex Numbers,
Sequences & Series, Calculus, Multivariable Calculus, Differential
Equations, and Linear Algebra. Difficulty increases as the player
progresses through a round, both within each topic and, taken as a whole,
across the topic list.

This started as a faithful Python port of the original C# console
application (Program.cs) and was subsequently extended with seven
additional topics reaching into more advanced mathematics. It uses only
the Python standard library (random, math, time, dataclasses, typing), so
it runs identically on Windows, macOS, and Linux with any modern Python 3
interpreter -- no external dependencies, no UI framework, no persistence.
"""

import functools
import json
import math
import os
import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Question:
    """A single generated question, its correct answer, and its time budget."""
    prompt: str
    answer: float
    tolerance: float
    time_limit_seconds: int


randomizer = random.Random()


# ---------------------------------------------------------------------------
# Entry point and main loop
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Math Quiz ===")
    print("Covers arithmetic, number theory, algebra, precalculus, geometry, trigonometry,")
    print("combinatorics, statistics, complex numbers, sequences & series, calculus,")
    print("multivariable calculus, differential equations, and linear algebra.")
    print()

    play_again = True
    while play_again:
        category = ask_for_category()
        question_count = ask_for_question_count()
        run_quiz(category, question_count)

        print()
        response = input("Play again? (y/n): ")
        play_again = response is not None and response.strip().lower().startswith("y")
        print()

    print("Thanks for playing!")


def ask_for_category() -> str:
    """Presents the topic menu and returns the chosen category key, or 'Mixed' for all topics."""
    names = list(categories.keys())

    print("Choose a topic:")
    for i, name in enumerate(names):
        print(f"  {i + 1}) {name}")
    print(f"  {len(names) + 1}) Mixed (all topics)")

    raw_input_value = input("Enter a number: ")

    choice = try_parse_int(raw_input_value)
    if choice is not None and 1 <= choice <= len(names):
        return names[choice - 1]

    return "Mixed"


def ask_for_question_count() -> int:
    """Asks how many questions the player wants, defaulting to 10 on bad input."""
    raw_input_value = input("How many questions? (default 10): ")

    count = try_parse_int(raw_input_value)
    if count is not None and count > 0:
        return count

    return 10


def run_quiz(category: str, question_count: int) -> None:
    """Runs a full quiz of the given length and topic, tracking score as it goes."""
    correct_count = 0
    missed_summaries: List[str] = []

    for i in range(question_count):
        progress = 1.0 if question_count <= 1 else i / (question_count - 1)
        question = generate_question(category, progress)

        print()
        print(f"Question {i + 1} of {question_count}")

        start_time = time.perf_counter()
        raw_answer = input(f"[{question.time_limit_seconds}s allowed] {question.prompt} = ")
        elapsed_seconds = time.perf_counter() - start_time

        within_time = elapsed_seconds <= question.time_limit_seconds
        user_answer = try_parse_float(raw_answer)
        parsed = user_answer is not None
        is_correct = (
            within_time
            and parsed
            and abs(user_answer - question.answer) <= question.tolerance
        )

        if is_correct:
            correct_count += 1
            print("Correct!")
        elif not within_time:
            print(f"Too slow! The answer was {format_answer(question.answer)}.")
            missed_summaries.append(f"{question.prompt} = {format_answer(question.answer)} (ran out of time)")
        else:
            print(f"Not quite. The answer was {format_answer(question.answer)}.")
            missed_summaries.append(f"{question.prompt} = {format_answer(question.answer)}")

    print()
    print(f"You got {correct_count} out of {question_count} correct.")

    if missed_summaries:
        print()
        print("Questions to review:")
        for summary in missed_summaries:
            print(f"  {summary}")


def generate_question(category: str, progress: float) -> Question:
    """Picks a generator appropriate for how far through the quiz the player is."""
    if category == "Mixed":
        real_categories = list(categories.keys())
        pool = categories[real_categories[randomizer.randrange(len(real_categories))]]
    else:
        pool = categories[category]

    target_index = round(progress * (len(pool) - 1))
    window_start = max(0, target_index - 1)
    chosen_index = randomizer.randint(window_start, target_index)

    return pool[chosen_index]()


CATEGORIES_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categories.json")


def build_categories(json_path: str = CATEGORIES_JSON_PATH) -> Dict[str, List[Callable[[], Question]]]:
    """Builds the full topic list from categories.json, each topic ordered roughly
    from easiest to hardest. The JSON holds only *what* generators to use and in what
    order/grouping (pure configuration); the generator functions themselves -- the
    actual math and randomization -- stay in this file since JSON can't express logic.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        raw_categories: Dict[str, List[dict]] = json.load(f)

    category_map: Dict[str, List[Callable[[], Question]]] = {}
    for topic, entries in raw_categories.items():
        pool: List[Callable[[], Question]] = []
        for entry in entries:
            generator_name = entry["generator"]
            if generator_name not in GENERATOR_REGISTRY:
                raise KeyError(
                    f"categories.json references unknown generator '{generator_name}' "
                    f"(topic '{topic}'). Check GENERATOR_REGISTRY in Program.py."
                )
            generator_func = GENERATOR_REGISTRY[generator_name]
            params = entry.get("params")
            pool.append(functools.partial(generator_func, **params) if params else generator_func)
        category_map[topic] = pool

    return category_map


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

def whole_addition(min_value: int, max_value: int) -> Question:
    a = randomizer.randint(min_value, max_value)
    b = randomizer.randint(min_value, max_value)
    return Question(f"{a} + {b}", a + b, 0.001, 12)


def whole_subtraction(min_value: int, max_value: int) -> Question:
    a = randomizer.randint(min_value, max_value)
    b = randomizer.randint(min_value, a)
    return Question(f"{a} - {b}", a - b, 0.001, 12)


def whole_multiplication(min_value: int, max_value: int) -> Question:
    a = randomizer.randint(min_value, max_value)
    b = randomizer.randint(min_value, max_value)
    return Question(f"{a} x {b}", a * b, 0.001, 15)


def whole_division(min_value: int, max_value: int) -> Question:
    divisor = randomizer.randint(min_value, max_value)
    quotient = randomizer.randint(min_value, max_value)
    dividend = divisor * quotient
    return Question(f"{dividend} / {divisor}", quotient, 0.001, 15)


def decimal_addition() -> Question:
    a = randomizer.randint(10, 499) / 10.0
    b = randomizer.randint(10, 499) / 10.0
    return Question(f"{a:.1f} + {b:.1f}", round(a + b, 1), 0.05, 18)


def decimal_subtraction() -> Question:
    a = randomizer.randint(50, 499) / 10.0
    b = randomizer.randint(0, int(a * 10) - 1) / 10.0
    return Question(f"{a:.1f} - {b:.1f}", round(a - b, 1), 0.05, 18)


def decimal_multiplication() -> Question:
    a = randomizer.randint(10, 99) / 10.0
    b = randomizer.randint(2, 9)
    return Question(f"{a:.1f} x {b}", round(a * b, 2), 0.1, 22)


def fraction_of_number() -> Question:
    denominators = [2, 3, 4, 5, 10]
    denominator = denominators[randomizer.randrange(len(denominators))]
    numerator = randomizer.randint(1, denominator - 1)
    multiplier = randomizer.randint(2, 11)
    whole = denominator * multiplier

    answer = numerator / denominator * whole
    return Question(f"{numerator}/{denominator} of {whole}", answer, 0.01, 20)


def percentage_of() -> Question:
    nice_percents = [5, 10, 15, 20, 25, 50, 75]
    percent = nice_percents[randomizer.randrange(len(nice_percents))]
    base_number = randomizer.randint(2, 40) * 4

    answer = round(base_number * percent / 100.0, 2)
    return Question(f"{percent}% of {base_number}", answer, 0.1, 20)


def percentage_change() -> Question:
    nice_percents = [10, 20, 25, 50]
    percent = nice_percents[randomizer.randrange(len(nice_percents))]
    base_number = randomizer.randint(10, 199)
    is_increase = randomizer.randrange(2) == 0

    if is_increase:
        answer = round(base_number * (1 + percent / 100.0), 2)
    else:
        answer = round(base_number * (1 - percent / 100.0), 2)

    action = "increased by" if is_increase else "decreased by"
    return Question(f"{base_number} {action} {percent}%", answer, 0.2, 24)


# ---------------------------------------------------------------------------
# Number Theory
# ---------------------------------------------------------------------------

def modulo_basic() -> Question:
    a = randomizer.randint(10, 99)
    b = randomizer.randint(2, 9)
    return Question(f"{a} mod {b}", a % b, 0.001, 15)


def gcd_two_numbers() -> Question:
    a = randomizer.randint(4, 60)
    b = randomizer.randint(4, 60)
    return Question(f"GCD of {a} and {b}", math.gcd(a, b), 0.001, 20)


def lcm_two_numbers() -> Question:
    a = randomizer.randint(2, 20)
    b = randomizer.randint(2, 20)
    answer = a * b // math.gcd(a, b)
    return Question(f"LCM of {a} and {b}", answer, 0.001, 22)


def divisor_count() -> Question:
    n = randomizer.randint(10, 100)
    count = sum(1 for d in range(1, n + 1) if n % d == 0)
    return Question(f"How many positive divisors does {n} have?", count, 0.001, 28)


def modular_exponentiation() -> Question:
    base = randomizer.randint(2, 9)
    exponent = randomizer.randint(2, 6)
    modulus = randomizer.randint(3, 13)
    answer = pow(base, exponent, modulus)
    return Question(f"{base}^{exponent} mod {modulus}", answer, 0.001, 30)


def euler_totient() -> Question:
    n = randomizer.randint(2, 40)
    count = sum(1 for k in range(1, n + 1) if math.gcd(k, n) == 1)
    return Question(
        f"Euler's totient phi({n}) -- how many integers from 1 to {n} are coprime with {n}?",
        count, 0.001, 35,
    )


# ---------------------------------------------------------------------------
# Algebra
# ---------------------------------------------------------------------------

def solve_addition_one_step() -> Question:
    x0 = randomizer.randint(1, 29)
    a = randomizer.randint(1, 29)
    b = x0 + a
    return Question(f"Solve for x: x + {a} = {b}", x0, 0.001, 15)


def solve_multiplication_one_step() -> Question:
    a = randomizer.randint(2, 11)
    x0 = randomizer.randint(1, 11)
    b = a * x0
    return Question(f"Solve for x: {a}x = {b}", x0, 0.001, 15)


def solve_two_step_linear() -> Question:
    a = randomizer.randint(2, 8)
    x0 = randomizer.randint(1, 11)
    b = randomizer.randint(1, 19)
    c = a * x0 + b
    return Question(f"Solve for x: {a}x + {b} = {c}", x0, 0.001, 20)


def evaluate_expression() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-6, 6)
    c = randomizer.randint(-6, 6)
    x0 = randomizer.randint(-4, 4)
    answer = a * x0 * x0 + b * x0 + c
    return Question(f"If x = {x0}, evaluate {a}x^2 + ({b})x + ({c})", answer, 0.001, 20)


def quadratic_larger_root() -> Question:
    p = randomizer.randint(-10, 10)
    q = p
    while q == p:
        q = randomizer.randint(-10, 10)

    answer = max(p, q)
    return Question(f"(x - ({p}))(x - ({q})) = 0. What is the larger solution for x?", answer, 0.001, 25)


def linear_system_solve_x() -> Question:
    x0 = randomizer.randint(1, 9)
    y0 = randomizer.randint(1, 9)

    determinant = 0
    a1 = b1 = a2 = b2 = 0
    while determinant == 0:
        a1 = randomizer.randint(1, 5)
        b1 = randomizer.randint(1, 5)
        a2 = randomizer.randint(1, 5)
        b2 = randomizer.randint(1, 5)
        determinant = a1 * b2 - a2 * b1

    c1 = a1 * x0 + b1 * y0
    c2 = a2 * x0 + b2 * y0

    prompt = f"{a1}x + {b1}y = {c1}; {a2}x + {b2}y = {c2}. Find x."
    return Question(prompt, x0, 0.01, 30)


# ---------------------------------------------------------------------------
# Precalculus
# ---------------------------------------------------------------------------

def function_composition_linear() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-5, 5)
    c = randomizer.randint(1, 5)
    d = randomizer.randint(-5, 5)
    x0 = randomizer.randint(-4, 4)
    inner = c * x0 + d
    answer = a * inner + b
    return Question(f"f(x) = {a}x + ({b}), g(x) = {c}x + ({d}). Find f(g({x0}))", answer, 0.001, 20)


def logarithm_basic() -> Question:
    base = randomizer.choice([2, 3, 5, 10])
    exponent = randomizer.randint(1, 5)
    value = base ** exponent
    return Question(f"log base {base} of {value}", exponent, 0.001, 20)


def exponential_evaluate() -> Question:
    base = randomizer.randint(2, 5)
    exponent = randomizer.randint(-3, 4)
    answer = base ** exponent
    return Question(f"{base}^({exponent})", answer, 0.01, 22)


def log_equation_solve() -> Question:
    base = randomizer.choice([2, 3, 5])
    x0 = randomizer.randint(1, 6)
    value = base ** x0
    return Question(f"Solve for x: {base}^x = {value}", x0, 0.001, 25)


def inverse_function_linear() -> Question:
    a = randomizer.randint(2, 9)
    b = randomizer.randint(-9, 9)
    x0 = randomizer.randint(-10, 10)
    y0 = a * x0 + b
    return Question(f"f(x) = {a}x + ({b}). Find f^-1({y0}) -- i.e. the x that gives this y", x0, 0.001, 28)


def natural_log_evaluate() -> Question:
    x0 = randomizer.randint(1, 50)
    answer = math.log(x0)
    return Question(f"ln({x0})", answer, 0.02, 25)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def rectangle_perimeter() -> Question:
    length = randomizer.randint(2, 29)
    width = randomizer.randint(2, 29)
    return Question(f"Perimeter of a rectangle with length {length} and width {width}", 2 * (length + width), 0.01, 15)


def rectangle_area() -> Question:
    length = randomizer.randint(2, 29)
    width = randomizer.randint(2, 29)
    return Question(f"Area of a rectangle with length {length} and width {width}", length * width, 0.01, 15)


def triangle_area() -> Question:
    base_length = randomizer.randint(2, 29)
    height = randomizer.randint(2, 29)
    return Question(f"Area of a triangle with base {base_length} and height {height}", 0.5 * base_length * height, 0.05, 18)


def circle_area() -> Question:
    radius = randomizer.randint(2, 19)
    answer = math.pi * radius * radius
    return Question(f"Area of a circle with radius {radius} (use pi = 3.14159)", answer, 0.5, 22)


def pythagorean_hypotenuse() -> Question:
    leg_a = randomizer.randint(3, 19)
    leg_b = randomizer.randint(3, 19)
    answer = math.sqrt(leg_a * leg_a + leg_b * leg_b)
    return Question(f"Hypotenuse of a right triangle with legs {leg_a} and {leg_b}", answer, 0.05, 20)


def rectangular_prism_volume() -> Question:
    length = randomizer.randint(2, 14)
    width = randomizer.randint(2, 14)
    height = randomizer.randint(2, 14)
    return Question(
        f"Volume of a rectangular prism with length {length}, width {width}, height {height}",
        length * width * height, 0.01, 20,
    )


# ---------------------------------------------------------------------------
# Trigonometry
# ---------------------------------------------------------------------------

COMMON_ANGLES = [0, 30, 45, 60, 90]


def degrees_to_radians(degrees: float) -> float:
    return degrees * math.pi / 180.0


def sine_of_common_angle() -> Question:
    angle = COMMON_ANGLES[randomizer.randrange(len(COMMON_ANGLES))]
    answer = math.sin(degrees_to_radians(angle))
    return Question(f"sin({angle} degrees)", answer, 0.01, 15)


def cosine_of_common_angle() -> Question:
    angle = COMMON_ANGLES[randomizer.randrange(len(COMMON_ANGLES))]
    answer = math.cos(degrees_to_radians(angle))
    return Question(f"cos({angle} degrees)", answer, 0.01, 15)


def tangent_of_common_angle() -> Question:
    valid_angles = [0, 30, 45, 60]  # 90 is undefined, excluded
    angle = valid_angles[randomizer.randrange(len(valid_angles))]
    answer = math.tan(degrees_to_radians(angle))
    return Question(f"tan({angle} degrees)", answer, 0.01, 15)


def triangle_missing_angle() -> Question:
    angle_a = randomizer.randint(20, 99)
    angle_b = randomizer.randint(20, 149 - angle_a)
    angle_c = 180 - angle_a - angle_b
    return Question(f"A triangle has angles {angle_a} and {angle_b} degrees. Find the third angle.", angle_c, 0.01, 15)


def right_triangle_opposite_side() -> Question:
    valid_angles = [30, 45, 60]
    angle = valid_angles[randomizer.randrange(len(valid_angles))]
    hypotenuse = randomizer.randint(5, 29)
    answer = hypotenuse * math.sin(degrees_to_radians(angle))
    return Question(
        f"Right triangle with hypotenuse {hypotenuse} and angle {angle} degrees. Find the opposite side.",
        answer, 0.1, 25,
    )


# ---------------------------------------------------------------------------
# Combinatorics
# ---------------------------------------------------------------------------

def factorial_value() -> Question:
    n = randomizer.randint(3, 8)
    return Question(f"{n}! (factorial)", math.factorial(n), 0.001, 15)


def permutations_count() -> Question:
    n = randomizer.randint(4, 10)
    r = randomizer.randint(2, n)
    answer = math.perm(n, r)
    return Question(
        f"How many ways to arrange {r} items chosen from {n} distinct items (order matters)? P({n},{r})",
        answer, 0.001, 24,
    )


def combinations_count() -> Question:
    n = randomizer.randint(4, 12)
    r = randomizer.randint(2, n)
    answer = math.comb(n, r)
    return Question(
        f"How many ways to choose {r} items from {n} distinct items (order doesn't matter)? C({n},{r})",
        answer, 0.001, 24,
    )


def coin_flip_probability() -> Question:
    n = randomizer.randint(3, 6)
    k = randomizer.randint(0, n)
    answer = round(math.comb(n, k) / (2 ** n), 4)
    return Question(f"Flipping a fair coin {n} times, what is P(exactly {k} heads)? (as a decimal)", answer, 0.001, 32)


# ---------------------------------------------------------------------------
# Calculus
# ---------------------------------------------------------------------------

def derivative_of_quadratic_at_point() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-6, 6)
    c = randomizer.randint(-6, 6)
    x0 = randomizer.randint(-4, 4)
    answer = 2 * a * x0 + b
    return Question(f"f(x) = {a}x^2 + ({b})x + ({c}). Find f'({x0})", answer, 0.01, 25)


def derivative_of_cubic_at_point() -> Question:
    a = randomizer.randint(1, 3)
    b = randomizer.randint(-4, 4)
    c = randomizer.randint(-4, 4)
    x0 = randomizer.randint(-3, 3)
    answer = 3 * a * x0 * x0 + 2 * b * x0 + c
    return Question(f"f(x) = {a}x^3 + ({b})x^2 + ({c})x. Find f'({x0})", answer, 0.01, 30)


def definite_integral_of_linear() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-5, 5)
    upper_bound = randomizer.randint(2, 7)
    answer = a / 2.0 * upper_bound * upper_bound + b * upper_bound
    return Question(f"Evaluate the definite integral of ({a}x + {b}) dx from 0 to {upper_bound}", answer, 0.05, 30)


def limit_at_infinity_ratio() -> Question:
    a = randomizer.randint(1, 8)
    b = randomizer.randint(1, 8)
    answer = a / b
    return Question(f"Find the limit as x approaches infinity of ({a}x + 7) / ({b}x - 3)", answer, 0.01, 25)


def limit_by_factoring() -> Question:
    p = randomizer.randint(2, 9)
    answer = 2 * p
    return Question(f"Find the limit as x approaches {p} of (x^2 - {p * p}) / (x - {p})", answer, 0.01, 25)


# ---------------------------------------------------------------------------
# Multivariable Calculus
# ---------------------------------------------------------------------------

def partial_derivative_x_at_point() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-5, 5)
    c = randomizer.randint(-5, 5)
    x0 = randomizer.randint(-4, 4)
    y0 = randomizer.randint(-4, 4)
    # f(x, y) = a*x^2 + b*x*y + c*y^2  ->  df/dx = 2ax + by
    answer = 2 * a * x0 + b * y0
    return Question(
        f"f(x,y) = {a}x^2 + ({b})xy + ({c})y^2. Find the partial derivative df/dx at ({x0}, {y0})",
        answer, 0.001, 30,
    )


def partial_derivative_y_at_point() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-5, 5)
    c = randomizer.randint(1, 5)
    x0 = randomizer.randint(-4, 4)
    y0 = randomizer.randint(-4, 4)
    # f(x, y) = a*x^2 + b*x*y + c*y^2  ->  df/dy = bx + 2cy
    answer = b * x0 + 2 * c * y0
    return Question(
        f"f(x,y) = {a}x^2 + ({b})xy + ({c})y^2. Find the partial derivative df/dy at ({x0}, {y0})",
        answer, 0.001, 30,
    )


def gradient_magnitude_at_point() -> Question:
    a = randomizer.randint(1, 4)
    b = randomizer.randint(1, 4)
    x0 = randomizer.randint(1, 6)
    y0 = randomizer.randint(1, 6)
    # f(x, y) = a*x^2 + b*y^2  ->  grad f = (2ax, 2by)
    gx = 2 * a * x0
    gy = 2 * b * y0
    answer = math.sqrt(gx * gx + gy * gy)
    return Question(f"f(x,y) = {a}x^2 + {b}y^2. Find the magnitude of the gradient at ({x0}, {y0})", answer, 0.05, 32)


def double_integral_over_rectangle() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(1, 5)
    x_max = randomizer.randint(2, 5)
    y_max = randomizer.randint(2, 5)
    # integral over [0, x_max] x [0, y_max] of (a*x + b*y) dA
    answer = a * (x_max ** 2) / 2 * y_max + b * (y_max ** 2) / 2 * x_max
    return Question(
        f"Evaluate the double integral of ({a}x + {b}y) dA over the rectangle [0,{x_max}] x [0,{y_max}]",
        answer, 0.05, 40,
    )


def divergence_at_point() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(1, 5)
    x0 = randomizer.randint(-4, 4)
    y0 = randomizer.randint(-4, 4)
    # F(x, y) = (a*x^2, b*y^2)  ->  div F = 2ax + 2by
    answer = 2 * a * x0 + 2 * b * y0
    return Question(f"Vector field F(x,y) = ({a}x^2, {b}y^2). Find the divergence of F at ({x0}, {y0})", answer, 0.001, 35)


# ---------------------------------------------------------------------------
# Differential Equations
# ---------------------------------------------------------------------------

def exponential_growth_at_time() -> Question:
    y0 = randomizer.randint(10, 100)
    k = randomizer.randint(1, 5) / 10.0
    t = randomizer.randint(1, 5)
    # dy/dt = k*y, y(0) = y0  ->  y(t) = y0 * e^(k*t)
    answer = y0 * math.exp(k * t)
    return Question(
        f"dy/dt = {k}y, y(0) = {y0}. Find y({t}) (exponential growth)",
        answer, max(answer * 0.02, 0.5), 32,
    )


def exponential_decay_half_life() -> Question:
    initial = randomizer.randint(100, 1000)
    half_life = randomizer.randint(2, 10)
    elapsed = half_life * randomizer.randint(1, 3)
    answer = initial * (0.5 ** (elapsed / half_life))
    return Question(
        f"A substance with half-life {half_life} years starts at {initial}g. How much remains after {elapsed} years?",
        answer, max(answer * 0.02, 0.5), 32,
    )


def newtons_law_of_cooling() -> Question:
    t_env = randomizer.randint(15, 25)
    t0 = randomizer.randint(70, 100)
    k = randomizer.randint(1, 3) / 10.0
    t = randomizer.randint(1, 5)
    # T(t) = T_env + (T0 - T_env) * e^(-k*t)
    answer = t_env + (t0 - t_env) * math.exp(-k * t)
    return Question(
        f"Newton's law of cooling: room temperature {t_env} degrees, object starts at {t0} degrees, "
        f"cooling constant k = {k}. Find the temperature at t = {t} (T(t) = T_env + (T0-T_env)e^(-kt))",
        answer, 0.5, 36,
    )


def characteristic_equation_larger_root() -> Question:
    p = randomizer.randint(-8, 8)
    q = p
    while q == p:
        q = randomizer.randint(-8, 8)
    b = -(p + q)
    c = p * q
    answer = max(p, q)
    return Question(
        f"For the ODE y'' + ({b})y' + ({c})y = 0, the characteristic equation has two real roots. Find the larger root.",
        answer, 0.001, 32,
    )


def logistic_growth_at_time() -> Question:
    carrying_capacity = randomizer.randint(500, 1000)
    p0 = randomizer.randint(10, 50)
    r = randomizer.randint(1, 3) / 10.0
    t = randomizer.randint(1, 5)
    # P(t) = K / (1 + ((K - P0) / P0) * e^(-r*t))
    answer = carrying_capacity / (1 + ((carrying_capacity - p0) / p0) * math.exp(-r * t))
    return Question(
        f"Logistic growth: carrying capacity {carrying_capacity}, P(0) = {p0}, growth rate r = {r}. Find P({t}).",
        answer, max(answer * 0.02, 1), 40,
    )


# ---------------------------------------------------------------------------
# Linear Algebra
# ---------------------------------------------------------------------------

def vector_addition_component() -> Question:
    a1 = randomizer.randint(-10, 10)
    a2 = randomizer.randint(-10, 10)
    b1 = randomizer.randint(-10, 10)
    b2 = randomizer.randint(-10, 10)
    return Question(f"u = ({a1}, {a2}), v = ({b1}, {b2}). Find the x-component of u + v", a1 + b1, 0.01, 18)


def vector_dot_product_2d() -> Question:
    a1 = randomizer.randint(-10, 10)
    a2 = randomizer.randint(-10, 10)
    b1 = randomizer.randint(-10, 10)
    b2 = randomizer.randint(-10, 10)
    answer = a1 * b1 + a2 * b2
    return Question(f"u = ({a1}, {a2}), v = ({b1}, {b2}). Find u . v (dot product)", answer, 0.01, 20)


def vector_magnitude_2d() -> Question:
    a1 = randomizer.randint(-12, 12)
    a2 = randomizer.randint(-12, 12)
    answer = math.sqrt(a1 * a1 + a2 * a2)
    return Question(f"Find the magnitude of vector u = ({a1}, {a2})", answer, 0.05, 22)


def matrix_determinant_2x2() -> Question:
    a = randomizer.randint(-8, 8)
    b = randomizer.randint(-8, 8)
    c = randomizer.randint(-8, 8)
    d = randomizer.randint(-8, 8)
    answer = a * d - b * c
    prompt = f"Determinant of matrix [[{a}, {b}], [{c}, {d}]]"
    return Question(prompt, answer, 0.01, 25)


def matrix_addition_entry() -> Question:
    a11 = randomizer.randint(-9, 9)
    a12 = randomizer.randint(-9, 9)
    b11 = randomizer.randint(-9, 9)
    b12 = randomizer.randint(-9, 9)
    prompt = f"A = [[{a11}, {a12}], [.., ..]], B = [[{b11}, {b12}], [.., ..]]. Find entry (1,1) of A + B"
    return Question(prompt, a11 + b11, 0.01, 20)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def generate_small_data_set(count: int, min_value: int, max_value: int) -> List[int]:
    return [randomizer.randint(min_value, max_value) for _ in range(count)]


def mean_of_list() -> Question:
    data = generate_small_data_set(5, 1, 50)
    answer = sum(data) / len(data)
    data_str = ", ".join(str(v) for v in data)
    return Question(f"Mean of {{{data_str}}}", answer, 0.05, 25)


def range_of_list() -> Question:
    data = generate_small_data_set(5, 1, 50)
    data_str = ", ".join(str(v) for v in data)
    return Question(f"Range of {{{data_str}}}", max(data) - min(data), 0.01, 20)


def median_of_list() -> Question:
    data = generate_small_data_set(5, 1, 50)  # Odd count keeps the median a single value
    sorted_data = sorted(data)
    answer = sorted_data[len(sorted_data) // 2]
    data_str = ", ".join(str(v) for v in data)
    return Question(f"Median of {{{data_str}}}", answer, 0.01, 25)


def simple_probability() -> Question:
    threshold = randomizer.randint(1, 5)  # 1 to 5
    favorable = 6 - threshold  # Outcomes on a six-sided die greater than the threshold
    answer = round(favorable / 6, 3)
    return Question(f"Rolling a fair six-sided die, what is P(roll > {threshold})? (as a decimal)", answer, 0.01, 20)


# ---------------------------------------------------------------------------
# Complex Numbers
# ---------------------------------------------------------------------------

def complex_addition_component() -> Question:
    a1 = randomizer.randint(-10, 10)
    b1 = randomizer.randint(-10, 10)
    a2 = randomizer.randint(-10, 10)
    b2 = randomizer.randint(-10, 10)
    return Question(f"z1 = {a1} + {b1}i, z2 = {a2} + {b2}i. Find the real part of z1 + z2", a1 + a2, 0.001, 18)


def complex_modulus() -> Question:
    a = randomizer.randint(-12, 12)
    b = randomizer.randint(-12, 12)
    answer = math.sqrt(a * a + b * b)
    return Question(f"Find the modulus |z| of z = {a} + {b}i", answer, 0.05, 22)


def complex_multiplication_component() -> Question:
    a1 = randomizer.randint(-9, 9)
    b1 = randomizer.randint(-9, 9)
    a2 = randomizer.randint(-9, 9)
    b2 = randomizer.randint(-9, 9)
    # (a1 + b1 i)(a2 + b2 i) = (a1*a2 - b1*b2) + (a1*b2 + a2*b1) i
    real = a1 * a2 - b1 * b2
    return Question(f"z1 = {a1} + {b1}i, z2 = {a2} + {b2}i. Find the real part of z1 * z2", real, 0.001, 28)


def complex_conjugate_modulus_squared() -> Question:
    a = randomizer.randint(-10, 10)
    b = randomizer.randint(-10, 10)
    answer = a * a + b * b
    return Question(f"z = {a} + {b}i. Find z times its complex conjugate (a real number)", answer, 0.001, 28)


def complex_power_de_moivre() -> Question:
    r = randomizer.randint(1, 4)
    angle_deg = randomizer.choice([0, 30, 45, 60, 90])
    n = randomizer.randint(2, 4)
    theta = math.radians(angle_deg)
    # De Moivre's theorem: z^n = r^n * (cos(n*theta) + i*sin(n*theta))
    answer = (r ** n) * math.cos(n * theta)
    return Question(
        f"z has modulus {r} and argument {angle_deg} degrees. Find the real part of z^{n} (De Moivre's theorem)",
        answer, 0.05, 38,
    )


# ---------------------------------------------------------------------------
# Sequences & Series
# ---------------------------------------------------------------------------

def arithmetic_sequence_nth_term() -> Question:
    a1 = randomizer.randint(1, 20)
    d = randomizer.randint(-5, 5)
    n = randomizer.randint(5, 20)
    answer = a1 + (n - 1) * d
    return Question(f"Arithmetic sequence: a1 = {a1}, common difference {d}. Find a{n}", answer, 0.001, 20)


def geometric_sequence_nth_term() -> Question:
    a1 = randomizer.randint(1, 5)
    r = randomizer.randint(2, 4)
    n = randomizer.randint(3, 7)
    answer = a1 * (r ** (n - 1))
    return Question(f"Geometric sequence: a1 = {a1}, common ratio {r}. Find a{n}", answer, 0.001, 24)


def arithmetic_series_sum() -> Question:
    a1 = randomizer.randint(1, 20)
    d = randomizer.randint(1, 6)
    n = randomizer.randint(5, 15)
    answer = n / 2 * (2 * a1 + (n - 1) * d)
    return Question(
        f"Sum of the first {n} terms of an arithmetic sequence with a1 = {a1} and common difference {d}",
        answer, 0.01, 28,
    )


def geometric_series_sum() -> Question:
    a1 = randomizer.randint(1, 5)
    r = randomizer.randint(2, 3)
    n = randomizer.randint(3, 6)
    answer = a1 * (r ** n - 1) / (r - 1)
    return Question(
        f"Sum of the first {n} terms of a geometric sequence with a1 = {a1} and common ratio {r}",
        answer, 0.01, 30,
    )


def infinite_geometric_series_sum() -> Question:
    a1 = randomizer.randint(1, 10)
    denominator = randomizer.randint(2, 5)  # ratio r = 1 / denominator, so |r| < 1 and the series converges
    r = 1 / denominator
    answer = a1 / (1 - r)
    return Question(
        f"Sum to infinity of a geometric series with a1 = {a1} and common ratio 1/{denominator}",
        answer, 0.01, 32,
    )


# ---------------------------------------------------------------------------
# Output formatting and parsing helpers
# ---------------------------------------------------------------------------

def format_answer(value: float) -> str:
    """Formats an answer for display, dropping unnecessary decimal zeros."""
    if value == math.floor(value):
        return f"{value:.0f}"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def try_parse_int(text: Optional[str]) -> Optional[int]:
    """Mirrors C#'s int.TryParse: returns None instead of raising on bad input."""
    if text is None:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None


def try_parse_float(text: Optional[str]) -> Optional[float]:
    """Mirrors C#'s double.TryParse(..., NumberStyles.Float, CultureInfo.InvariantCulture, ...)."""
    if text is None:
        return None
    try:
        return float(text.strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Generator registry -- maps the string names used in categories.json to the
# actual generator functions defined above. Every generator referenced by
# categories.json must have an entry here.
# ---------------------------------------------------------------------------

GENERATOR_REGISTRY: Dict[str, Callable[..., Question]] = {
    # Arithmetic
    "whole_addition": whole_addition,
    "whole_subtraction": whole_subtraction,
    "whole_multiplication": whole_multiplication,
    "whole_division": whole_division,
    "decimal_addition": decimal_addition,
    "decimal_subtraction": decimal_subtraction,
    "fraction_of_number": fraction_of_number,
    "percentage_of": percentage_of,
    "decimal_multiplication": decimal_multiplication,
    "percentage_change": percentage_change,
    # Number Theory
    "modulo_basic": modulo_basic,
    "gcd_two_numbers": gcd_two_numbers,
    "lcm_two_numbers": lcm_two_numbers,
    "divisor_count": divisor_count,
    "modular_exponentiation": modular_exponentiation,
    "euler_totient": euler_totient,
    # Algebra
    "solve_addition_one_step": solve_addition_one_step,
    "solve_multiplication_one_step": solve_multiplication_one_step,
    "solve_two_step_linear": solve_two_step_linear,
    "evaluate_expression": evaluate_expression,
    "quadratic_larger_root": quadratic_larger_root,
    "linear_system_solve_x": linear_system_solve_x,
    # Precalculus
    "function_composition_linear": function_composition_linear,
    "logarithm_basic": logarithm_basic,
    "exponential_evaluate": exponential_evaluate,
    "log_equation_solve": log_equation_solve,
    "inverse_function_linear": inverse_function_linear,
    "natural_log_evaluate": natural_log_evaluate,
    # Geometry
    "rectangle_perimeter": rectangle_perimeter,
    "rectangle_area": rectangle_area,
    "triangle_area": triangle_area,
    "circle_area": circle_area,
    "pythagorean_hypotenuse": pythagorean_hypotenuse,
    "rectangular_prism_volume": rectangular_prism_volume,
    # Trigonometry
    "sine_of_common_angle": sine_of_common_angle,
    "cosine_of_common_angle": cosine_of_common_angle,
    "tangent_of_common_angle": tangent_of_common_angle,
    "triangle_missing_angle": triangle_missing_angle,
    "right_triangle_opposite_side": right_triangle_opposite_side,
    # Combinatorics
    "factorial_value": factorial_value,
    "permutations_count": permutations_count,
    "combinations_count": combinations_count,
    "coin_flip_probability": coin_flip_probability,
    # Statistics
    "mean_of_list": mean_of_list,
    "range_of_list": range_of_list,
    "median_of_list": median_of_list,
    "simple_probability": simple_probability,
    # Complex Numbers
    "complex_addition_component": complex_addition_component,
    "complex_modulus": complex_modulus,
    "complex_multiplication_component": complex_multiplication_component,
    "complex_conjugate_modulus_squared": complex_conjugate_modulus_squared,
    "complex_power_de_moivre": complex_power_de_moivre,
    # Sequences & Series
    "arithmetic_sequence_nth_term": arithmetic_sequence_nth_term,
    "geometric_sequence_nth_term": geometric_sequence_nth_term,
    "arithmetic_series_sum": arithmetic_series_sum,
    "geometric_series_sum": geometric_series_sum,
    "infinite_geometric_series_sum": infinite_geometric_series_sum,
    # Calculus
    "derivative_of_quadratic_at_point": derivative_of_quadratic_at_point,
    "derivative_of_cubic_at_point": derivative_of_cubic_at_point,
    "definite_integral_of_linear": definite_integral_of_linear,
    "limit_at_infinity_ratio": limit_at_infinity_ratio,
    "limit_by_factoring": limit_by_factoring,
    # Multivariable Calculus
    "partial_derivative_x_at_point": partial_derivative_x_at_point,
    "partial_derivative_y_at_point": partial_derivative_y_at_point,
    "gradient_magnitude_at_point": gradient_magnitude_at_point,
    "double_integral_over_rectangle": double_integral_over_rectangle,
    "divergence_at_point": divergence_at_point,
    # Differential Equations
    "exponential_growth_at_time": exponential_growth_at_time,
    "exponential_decay_half_life": exponential_decay_half_life,
    "newtons_law_of_cooling": newtons_law_of_cooling,
    "characteristic_equation_larger_root": characteristic_equation_larger_root,
    "logistic_growth_at_time": logistic_growth_at_time,
    # Linear Algebra
    "vector_addition_component": vector_addition_component,
    "vector_dot_product_2d": vector_dot_product_2d,
    "vector_magnitude_2d": vector_magnitude_2d,
    "matrix_determinant_2x2": matrix_determinant_2x2,
    "matrix_addition_entry": matrix_addition_entry,
}


# ---------------------------------------------------------------------------
# Module-level initialization (mirrors the C# static field initializer)
# ---------------------------------------------------------------------------

categories: Dict[str, List[Callable[[], Question]]] = build_categories()


if __name__ == "__main__":
    main()