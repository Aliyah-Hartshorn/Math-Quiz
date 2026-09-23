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
interpreter -- no external dependencies, no UI framework.

Features inherited from the C# version include: a full menu system
(Start Quiz, Instructions, View Statistics, Exit), difficulty selection
(Easy / Medium / Hard / Mixed), hints, a points system with streak
bonuses, quiz results display, high-score tracking, per-category
statistics with file persistence, and review summaries for missed
questions.
"""

import functools
import json
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Question:
    """A single generated question, its correct answer, time budget, hint, and explanation."""
    prompt: str
    answer: float
    tolerance: float
    time_limit_seconds: int
    hint: str = ""
    explanation: str = ""
    points: int = 0


@dataclass
class QuizResult:
    """Aggregate results from a single quiz run."""
    correct: int = 0
    questions: int = 0
    points: int = 0
    best_streak: int = 0
    average_time: float = 0.0
    category: str = ""
    difficulty: str = ""


@dataclass
class CategoryStats:
    """Per-category running statistics."""
    correct: int = 0
    attempted: int = 0


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

randomizer = random.Random()

# Statistics file path
STATISTICS_FILE = "mathquiz_stats.txt"

# Global statistics
high_score: int = 0
total_correct: int = 0
total_questions: int = 0
games_played: int = 0
statistics: Dict[str, CategoryStats] = {}


# ---------------------------------------------------------------------------
# Entry point and main loop
# ---------------------------------------------------------------------------

def main() -> None:
    """Program entry point: loads stats, runs the main menu loop, saves on exit."""
    load_statistics()

    running = True
    while running:
        clear_screen()
        show_title()

        print("1) Start Quiz")
        print("2) Instructions")
        print("3) View Statistics")
        print("4) Exit")
        print()

        choice = read_int("Choose an option: ", 1, 4)

        if choice == 1:
            start_quiz()
        elif choice == 2:
            show_instructions()
        elif choice == 3:
            show_statistics()
        elif choice == 4:
            running = False

    save_statistics()

    clear_screen()
    print("=================================")
    print("        Thanks for playing!")
    print("=================================")


# ---------------------------------------------------------------------------
# Main menu and setup
# ---------------------------------------------------------------------------

def show_title() -> None:
    """Prints the banner title."""
    print("=================================")
    print("            MATH QUIZ")
    print("=================================")
    print("Arithmetic | Number Theory | Algebra | Precalculus")
    print("Geometry | Trigonometry | Combinatorics | Statistics")
    print("Complex Numbers | Sequences & Series | Calculus")
    print("Multivariable Calculus | Differential Equations | Linear Algebra")
    print()


def start_quiz() -> None:
    """Runs the full quiz setup flow: category, difficulty, count, then quiz."""
    clear_screen()
    show_title()

    category = ask_for_category()
    difficulty = ask_for_difficulty()
    question_count = ask_for_question_count()

    clear_screen()
    show_title()

    print(f"Category:   {category}")
    print(f"Difficulty: {difficulty}")
    print(f"Questions:  {question_count}")
    print()
    print("Type Q at any question to end the quiz.")
    print("Press ENTER to begin.")

    input()

    result = run_quiz(category, difficulty, question_count)

    show_results(result)
    save_statistics()

    print()
    print("Press ENTER to return to the main menu.")
    input()


def ask_for_category() -> str:
    """Presents the topic menu and returns the chosen category key, or 'Mixed' for all topics."""
    names = list(categories.keys())

    print("Choose a topic:")
    for i, name in enumerate(names):
        print(f"  {i + 1}) {name}")
    print(f"  {len(names) + 1}) Mixed (all topics)")
    print()

    choice = read_int("Enter a number: ", 1, len(names) + 1)

    if choice == len(names) + 1:
        return "Mixed"

    return names[choice - 1]


def ask_for_difficulty() -> str:
    """Presents the difficulty menu and returns the chosen level."""
    print()
    print("Choose difficulty:")
    print("  1) Easy")
    print("  2) Medium")
    print("  3) Hard")
    print("  4) Mixed")
    print()

    choice = read_int("Enter a number: ", 1, 4)

    if choice == 1:
        return "Easy"
    elif choice == 2:
        return "Medium"
    elif choice == 3:
        return "Hard"
    else:
        return "Mixed"


def ask_for_question_count() -> int:
    """Asks how many questions the player wants (1-50)."""
    print()
    return read_int("How many questions? (1-50): ", 1, 50)


def read_int(message: str, minimum: int, maximum: int) -> int:
    """Reads and validates an integer within [minimum, maximum]."""
    while True:
        user_input = input(message)
        value = try_parse_int(user_input)
        if value is not None and minimum <= value <= maximum:
            return value
        print(f"Invalid input. Please enter a number from {minimum} to {maximum}.")


# ---------------------------------------------------------------------------
# Instructions
# ---------------------------------------------------------------------------

def show_instructions() -> None:
    """Displays the how-to-play screen."""
    clear_screen()
    show_title()

    print("HOW TO PLAY")
    print("---------------------------------")
    print("1. Choose a mathematics category.")
    print("2. Select a difficulty level.")
    print("3. Choose between 1 and 50 questions.")
    print("4. Answer before the timer expires.")
    print("5. Correct answers earn points.")
    print("6. Consecutive correct answers build a streak.")
    print("7. A hint can be used, but reduces the points for that question.")
    print("8. Type Q to end a quiz early.")
    print("9. Incorrect questions are shown at the end.")
    print("10. Your overall statistics and high score are saved.")
    print()
    print("DIFFICULTY")
    print("---------------------------------")
    print("Easy   = introductory questions")
    print("Medium = more calculations and multi-step questions")
    print("Hard   = advanced questions and less time")
    print()
    print("Press ENTER to return to the main menu.")
    input()


# ---------------------------------------------------------------------------
# Quiz engine
# ---------------------------------------------------------------------------

def run_quiz(category: str, difficulty: str, question_count: int) -> QuizResult:
    """Runs a full quiz of the given length, topic, and difficulty, tracking score."""
    correct_count = 0
    total_points = 0
    current_streak = 0
    best_streak = 0
    total_time = 0.0
    answered_questions = 0
    missed_summaries: List[str] = []

    for i in range(question_count):
        progress = 1.0 if question_count <= 1 else i / (question_count - 1)
        question = generate_question(category, difficulty, progress)

        clear_screen()
        show_title()

        print(f"Category: {category}")
        print(f"Difficulty: {difficulty}")
        print(f"Question {i + 1} of {question_count}")
        print(f"Current streak: {current_streak}")
        print(f"Best streak this quiz: {best_streak}")
        print(f"Points: {total_points}")
        print()
        print(f"[{question.time_limit_seconds}s allowed]")
        print(question.prompt)
        print()
        print("Type H for a hint or Q to quit.")
        print("Answer: ", end="")

        start_time = time.perf_counter()
        raw_answer = input()
        elapsed_seconds = time.perf_counter() - start_time

        if raw_answer.strip().lower() == "q":
            print()
            print("Quiz ended early.")
            break

        used_hint = False

        if raw_answer.strip().lower() == "h":
            used_hint = True
            print()
            print(f"Hint: {question.hint}")
            print("Answer: ", end="")

            start_time = time.perf_counter()
            raw_answer = input()
            elapsed_seconds += time.perf_counter() - start_time

            if raw_answer.strip().lower() == "q":
                print()
                print("Quiz ended early.")
                break

        answered_questions += 1
        total_time += elapsed_seconds

        within_time = elapsed_seconds <= question.time_limit_seconds
        user_answer = try_parse_float(raw_answer)
        parsed = user_answer is not None

        is_correct = (
            within_time
            and parsed
            and abs(user_answer - question.answer) <= question.tolerance
        )

        points_earned = 0

        if is_correct:
            correct_count += 1
            current_streak += 1

            if current_streak > best_streak:
                best_streak = current_streak

            points_earned = question.points

            if used_hint:
                points_earned = max(1, points_earned // 2)

            # Streak bonuses.
            if current_streak >= 5:
                points_earned += 20
            elif current_streak >= 3:
                points_earned += 10

            total_points += points_earned

            print()
            print(f"Correct! +{points_earned} points")

            if current_streak >= 3:
                print(f"\U0001f525 {current_streak} question streak!")
        else:
            current_streak = 0
            print()

            if not within_time:
                print("Too slow!")
                missed_summaries.append(
                    build_review_summary(question, raw_answer, "Ran out of time")
                )
            elif not parsed:
                print("That was not a valid number.")
                missed_summaries.append(
                    build_review_summary(question, raw_answer, "Invalid answer")
                )
            else:
                print("Not quite.")
                missed_summaries.append(
                    build_review_summary(question, raw_answer, "Incorrect")
                )

            print(f"Correct answer: {format_answer(question.answer)}")
            print(f"Explanation: {question.explanation}")

        update_category_statistics(category, is_correct)
        global total_correct, total_questions
        total_correct += 1 if is_correct else 0
        total_questions += 1

        print()
        print("Press ENTER to continue.")
        input()

    global games_played
    games_played += 1

    average_time = total_time / answered_questions if answered_questions > 0 else 0.0

    return QuizResult(
        correct=correct_count,
        questions=answered_questions,
        points=total_points,
        best_streak=best_streak,
        average_time=average_time,
        category=category,
        difficulty=difficulty,
    )


def build_review_summary(question: Question, user_answer: str, result: str) -> str:
    """Builds a multi-line review string for a missed question."""
    display_answer = user_answer.strip() if user_answer.strip() else "(no answer)"
    return (
        f"{question.prompt}\n"
        f"   Your answer: {display_answer}\n"
        f"   Correct answer: {format_answer(question.answer)}\n"
        f"   Result: {result}\n"
        f"   Explanation: {question.explanation}"
    )


def show_results(result: QuizResult) -> None:
    """Displays the quiz results summary."""
    global high_score

    clear_screen()
    show_title()

    percentage = (result.correct / result.questions * 100) if result.questions > 0 else 0

    print("========== QUIZ RESULTS ==========")
    print()
    print(f"Category:       {result.category}")
    print(f"Difficulty:     {result.difficulty}")
    print(f"Correct:        {result.correct}/{result.questions}")
    print(f"Percentage:     {percentage:0.0f}%")
    print(f"Points:         {result.points}")
    print(f"Best streak:    {result.best_streak}")
    print(f"Average time:   {result.average_time:0.1f} seconds")
    print()

    if result.points > high_score:
        high_score = result.points
        print("NEW HIGH SCORE!")
    else:
        print(f"High score:     {high_score}")

    print()
    print("==================================")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def update_category_statistics(category: str, correct: bool) -> None:
    """Updates the per-category statistics. Ignores 'Mixed' category."""
    if category == "Mixed":
        return

    if category not in statistics:
        statistics[category] = CategoryStats()

    statistics[category].attempted += 1

    if correct:
        statistics[category].correct += 1


def show_statistics() -> None:
    """Displays overall and per-category statistics."""
    clear_screen()
    show_title()

    print("========== STATISTICS ==========")
    print()
    print(f"Games played:   {games_played}")
    print(f"Total questions: {total_questions}")
    print(f"Total correct:   {total_correct}")
    print(f"High score:      {high_score}")

    overall_percentage = (total_correct / total_questions * 100) if total_questions > 0 else 0

    print(f"Overall accuracy: {overall_percentage:6.1f}%")
    print()

    print("CATEGORY STATISTICS")
    print("---------------------------------")

    for category in categories.keys():
        stats = statistics.get(category, CategoryStats())
        percentage = (stats.correct / stats.attempted * 100) if stats.attempted > 0 else 0
        print(f"{category:<22} {stats.correct:>3}/{stats.attempted:<3} ({percentage:0.1f}%)")

    print()
    print("Press ENTER to return to the main menu.")
    input()


def load_statistics() -> None:
    """Loads statistics from the stats file. Starts fresh on any error."""
    global high_score, total_correct, total_questions, games_played, statistics

    try:
        if not os.path.exists(STATISTICS_FILE):
            return

        with open(STATISTICS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split("|")

            if len(parts) == 2:
                key, value = parts[0], parts[1]
                if key == "HighScore":
                    high_score = try_parse_int(value) or 0
                elif key == "TotalCorrect":
                    total_correct = try_parse_int(value) or 0
                elif key == "TotalQuestions":
                    total_questions = try_parse_int(value) or 0
                elif key == "GamesPlayed":
                    games_played = try_parse_int(value) or 0
            elif len(parts) == 4 and parts[0] == "Category":
                name = parts[1]
                correct = try_parse_int(parts[2]) or 0
                attempted = try_parse_int(parts[3]) or 0
                statistics[name] = CategoryStats(correct=correct, attempted=attempted)

    except Exception:
        statistics.clear()


def save_statistics() -> None:
    """Saves statistics to the stats file. Silently ignores errors."""
    try:
        lines = [
            f"HighScore|{high_score}",
            f"TotalCorrect|{total_correct}",
            f"TotalQuestions|{total_questions}",
            f"GamesPlayed|{games_played}",
        ]

        for key, value in statistics.items():
            lines.append(f"Category|{key}|{value.correct}|{value.attempted}")

        with open(STATISTICS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    except Exception:
        pass


# ---------------------------------------------------------------------------
# Question selection
# ---------------------------------------------------------------------------

def generate_question(category: str, difficulty: str, progress: float) -> Question:
    """Picks a generator appropriate for how far through the quiz the player is,
    filtered by difficulty."""
    if category == "Mixed":
        real_categories = list(categories.keys())
        selected_category = real_categories[randomizer.randrange(len(real_categories))]
        pool = categories[selected_category]
    else:
        pool = categories[category]

    filtered_pool = filter_by_difficulty(pool, difficulty)

    if len(filtered_pool) == 0:
        filtered_pool = pool

    target_index = round(progress * (len(filtered_pool) - 1))

    # Select from a small area around the target so the quiz
    # becomes gradually harder without becoming predictable.
    window_start = max(0, target_index - 1)
    window_end = min(len(filtered_pool) - 1, target_index + 1)

    chosen_index = randomizer.randint(window_start, window_end)

    return filtered_pool[chosen_index]()


def filter_by_difficulty(pool: List[Callable[[], Question]], difficulty: str) -> List[Callable[[], Question]]:
    """Filters the generator pool by difficulty, splitting into thirds."""
    if difficulty == "Mixed":
        return list(pool)

    count = len(pool)

    if difficulty == "Easy":
        return pool[: max(1, count // 3)]

    if difficulty == "Medium":
        start = count // 3
        length = max(1, count // 3)
        return pool[start : start + length]

    # Hard
    return pool[max(0, (count * 2) // 3) :]


# ---------------------------------------------------------------------------
# Category configuration (loaded from categories.json)
# ---------------------------------------------------------------------------

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
                    f"(topic '{topic}'). Check GENERATOR_REGISTRY in this file."
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
    return make_question(
        f"{a} + {b}",
        a + b,
        12,
        "Add the two numbers.",
        f"Add {a} and {b}.",
    )


def whole_subtraction(min_value: int, max_value: int) -> Question:
    a = randomizer.randint(min_value, max_value)
    b = randomizer.randint(min_value, a)
    return make_question(
        f"{a} - {b}",
        a - b,
        12,
        "Subtract the smaller number from the larger number.",
        f"Calculate {a} minus {b}.",
    )


def whole_multiplication(min_value: int, max_value: int) -> Question:
    a = randomizer.randint(min_value, max_value)
    b = randomizer.randint(min_value, max_value)
    return make_question(
        f"{a} x {b}",
        a * b,
        15,
        "Use multiplication.",
        f"Calculate {a} groups of {b}.",
    )


def whole_division(min_value: int, max_value: int) -> Question:
    divisor = randomizer.randint(min_value, max_value)
    quotient = randomizer.randint(min_value, max_value)
    dividend = divisor * quotient
    return make_question(
        f"{dividend} / {divisor}",
        quotient,
        15,
        "Think about the multiplication fact that gives the dividend.",
        f"{dividend} divided by {divisor} equals {quotient}.",
    )


def decimal_addition() -> Question:
    a = randomizer.randint(10, 499) / 10.0
    b = randomizer.randint(10, 499) / 10.0
    return make_question(
        f"{a:.1f} + {b:.1f}",
        round(a + b, 1),
        18,
        "Line up the decimal places.",
        "Add the numbers while keeping the decimal place aligned.",
    )


def decimal_subtraction() -> Question:
    a = randomizer.randint(50, 499) / 10.0
    b = randomizer.randint(0, int(a * 10) - 1) / 10.0
    return make_question(
        f"{a:.1f} - {b:.1f}",
        round(a - b, 1),
        18,
        "Line up the decimal places.",
        "Subtract the second decimal from the first.",
    )


def decimal_multiplication() -> Question:
    a = randomizer.randint(10, 99) / 10.0
    b = randomizer.randint(2, 9)
    return make_question(
        f"{a:.1f} x {b}",
        round(a * b, 2),
        22,
        "Multiply first, then place the decimal.",
        "Multiply the decimal by the whole number.",
    )


def fraction_of_number() -> Question:
    denominators = [2, 3, 4, 5, 10]
    denominator = denominators[randomizer.randrange(len(denominators))]
    numerator = randomizer.randint(1, denominator - 1)
    multiplier = randomizer.randint(2, 11)
    whole = denominator * multiplier

    answer = numerator / denominator * whole
    return make_question(
        f"{numerator}/{denominator} of {whole}",
        answer,
        20,
        "Divide by the denominator, then multiply by the numerator.",
        "A fraction of a number can be found using fraction x whole number.",
    )


def percentage_of() -> Question:
    nice_percents = [5, 10, 15, 20, 25, 50, 75]
    percent = nice_percents[randomizer.randrange(len(nice_percents))]
    base_number = randomizer.randint(2, 40) * 4

    answer = round(base_number * percent / 100.0, 2)
    return make_question(
        f"{percent}% of {base_number}",
        answer,
        20,
        "Convert the percentage to a decimal.",
        f"{percent}% means {percent}/100.",
    )


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
    return make_question(
        f"{base_number} {action} {percent}%",
        answer,
        24,
        "For an increase multiply by 1 + percentage. For a decrease multiply by 1 - percentage.",
        f"Apply a {percent}% change to {base_number}.",
    )


def order_of_operations() -> Question:
    a = randomizer.randint(2, 9)
    b = randomizer.randint(2, 9)
    c = randomizer.randint(1, 9)
    answer = a + b * c
    return make_question(
        f"{a} + {b} x {c}",
        answer,
        20,
        "Remember BIDMAS/BODMAS: multiplication comes before addition.",
        "Multiply first, then add.",
    )


def fraction_addition() -> Question:
    denominator = randomizer.randint(2, 7)
    numerator1 = randomizer.randint(1, denominator - 1)
    numerator2 = randomizer.randint(1, denominator - 1)
    answer = (numerator1 + numerator2) / denominator
    return make_question(
        f"{numerator1}/{denominator} + {numerator2}/{denominator}",
        answer,
        20,
        "The denominators are already the same.",
        "Add the numerators and keep the denominator.",
    )


def ratio_question() -> Question:
    ratio_a = randomizer.randint(1, 5)
    ratio_b = randomizer.randint(1, 5)
    multiplier = randomizer.randint(2, 9)
    first_amount = ratio_a * multiplier
    return make_question(
        f"A ratio is {ratio_a}:{ratio_b}. If the first amount is {first_amount}, what is the second amount?",
        ratio_b * multiplier,
        25,
        f"Find the multiplier: {first_amount} / {ratio_a}.",
        f"The ratio is multiplied by {multiplier}.",
    )


def square_root_question() -> Question:
    root = randomizer.randint(2, 12)
    value = root * root
    return make_question(
        f"\u221a{value}",
        root,
        18,
        "Think of a number multiplied by itself.",
        f"{root} x {root} = {value}.",
    )


# ---------------------------------------------------------------------------
# Number Theory
# ---------------------------------------------------------------------------

def modulo_basic() -> Question:
    a = randomizer.randint(10, 99)
    b = randomizer.randint(2, 9)
    return make_question(
        f"{a} mod {b}",
        a % b,
        15,
        "Find the remainder after division.",
        f"{a} divided by {b} leaves remainder {a % b}.",
    )


def gcd_two_numbers() -> Question:
    a = randomizer.randint(4, 60)
    b = randomizer.randint(4, 60)
    return make_question(
        f"GCD of {a} and {b}",
        math.gcd(a, b),
        20,
        "Find the largest number that divides both.",
        f"The greatest common divisor is {math.gcd(a, b)}.",
    )


def lcm_two_numbers() -> Question:
    a = randomizer.randint(2, 20)
    b = randomizer.randint(2, 20)
    answer = a * b // math.gcd(a, b)
    return make_question(
        f"LCM of {a} and {b}",
        answer,
        22,
        "Use the formula: LCM = a * b / GCD(a, b).",
        f"The least common multiple is {answer}.",
    )


def divisor_count() -> Question:
    n = randomizer.randint(10, 100)
    count = sum(1 for d in range(1, n + 1) if n % d == 0)
    return make_question(
        f"How many positive divisors does {n} have?",
        count,
        28,
        "Check every number from 1 to n that divides evenly.",
        f"{n} has {count} positive divisors.",
    )


def modular_exponentiation() -> Question:
    base = randomizer.randint(2, 9)
    exponent = randomizer.randint(2, 6)
    modulus = randomizer.randint(3, 13)
    answer = pow(base, exponent, modulus)
    return make_question(
        f"{base}^{exponent} mod {modulus}",
        answer,
        30,
        "Compute the power first, then take the remainder.",
        f"{base}^{exponent} mod {modulus} = {answer}.",
    )


def euler_totient() -> Question:
    n = randomizer.randint(2, 40)
    count = sum(1 for k in range(1, n + 1) if math.gcd(k, n) == 1)
    return make_question(
        f"Euler's totient phi({n}) -- how many integers from 1 to {n} are coprime with {n}?",
        count,
        35,
        "Count numbers sharing no common factor with n.",
        f"phi({n}) = {count}.",
    )


# ---------------------------------------------------------------------------
# Algebra
# ---------------------------------------------------------------------------

def solve_addition_one_step() -> Question:
    x0 = randomizer.randint(1, 29)
    a = randomizer.randint(1, 29)
    b = x0 + a
    return make_question(
        f"Solve for x: x + {a} = {b}",
        x0,
        15,
        f"Subtract {a} from both sides.",
        f"x = {b} - {a}.",
    )


def solve_multiplication_one_step() -> Question:
    a = randomizer.randint(2, 11)
    x0 = randomizer.randint(1, 11)
    b = a * x0
    return make_question(
        f"Solve for x: {a}x = {b}",
        x0,
        15,
        f"Divide both sides by {a}.",
        f"x = {b} / {a}.",
    )


def solve_two_step_linear() -> Question:
    a = randomizer.randint(2, 8)
    x0 = randomizer.randint(1, 11)
    b = randomizer.randint(1, 19)
    c = a * x0 + b
    return make_question(
        f"Solve for x: {a}x + {b} = {c}",
        x0,
        20,
        f"Subtract {b}, then divide by {a}.",
        f"x = ({c} - {b}) / {a}.",
    )


def evaluate_expression() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-6, 6)
    c = randomizer.randint(-6, 6)
    x0 = randomizer.randint(-4, 4)
    answer = a * x0 * x0 + b * x0 + c
    return make_question(
        f"If x = {x0}, evaluate {a}x^2 + ({b})x + ({c})",
        answer,
        20,
        f"Substitute x = {x0} into the expression.",
        "Replace every x with the given value, then calculate.",
    )


def quadratic_larger_root() -> Question:
    p = randomizer.randint(-10, 10)
    q = p
    while q == p:
        q = randomizer.randint(-10, 10)

    answer = max(p, q)
    return make_question(
        f"(x - ({p}))(x - ({q})) = 0. What is the larger solution for x?",
        answer,
        25,
        "Set each bracket equal to zero.",
        f"The two solutions are x = {p} and x = {q}.",
    )


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
    return make_question(
        prompt,
        x0,
        30,
        "Use elimination to remove y.",
        f"The generated solution has x = {x0}.",
    )


def expand_brackets() -> Question:
    a = randomizer.randint(2, 7)
    b = randomizer.randint(1, 7)
    answer = a * b
    return make_question(
        f"Find the constant term when expanding (x + {a})(x + {b})",
        answer,
        25,
        "Multiply the two constants.",
        f"{a} x {b} = {answer}.",
    )


def factorise_quadratic() -> Question:
    a = randomizer.randint(1, 7)
    b = randomizer.randint(1, 7)
    answer = a + b
    return make_question(
        f"For x^2 + {a + b}x + {a * b}, enter the sum of the two factor values.",
        answer,
        25,
        f"The factors multiply to {a * b}.",
        f"The factor values are {a} and {b}, whose sum is {a + b}.",
    )


def solve_quadratic() -> Question:
    root = randomizer.randint(-6, 6)
    constant = root * root
    return make_question(
        f"Solve x^2 = {constant}. Enter the positive solution.",
        abs(root),
        22,
        "Take the square root of both sides.",
        f"The positive square root of {constant} is {abs(root)}.",
    )


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
    return make_question(
        f"f(x) = {a}x + ({b}), g(x) = {c}x + ({d}). Find f(g({x0}))",
        answer,
        20,
        "Evaluate g(x0) first, then substitute into f.",
        f"g({x0}) = {inner}, then f({inner}) = {answer}.",
    )


def logarithm_basic() -> Question:
    base = randomizer.choice([2, 3, 5, 10])
    exponent = randomizer.randint(1, 5)
    value = base ** exponent
    return make_question(
        f"log base {base} of {value}",
        exponent,
        20,
        f"Ask: {base} to what power equals {value}?",
        f"{base}^{exponent} = {value}, so log = {exponent}.",
    )


def exponential_evaluate() -> Question:
    base = randomizer.randint(2, 5)
    exponent = randomizer.randint(-3, 4)
    answer = base ** exponent
    return make_question(
        f"{base}^({exponent})",
        answer,
        22,
        "Multiply the base by itself the given number of times.",
        f"{base}^{exponent} = {answer}.",
    )


def log_equation_solve() -> Question:
    base = randomizer.choice([2, 3, 5])
    x0 = randomizer.randint(1, 6)
    value = base ** x0
    return make_question(
        f"Solve for x: {base}^x = {value}",
        x0,
        25,
        f"Express {value} as a power of {base}.",
        f"{base}^{x0} = {value}, so x = {x0}.",
    )


def inverse_function_linear() -> Question:
    a = randomizer.randint(2, 9)
    b = randomizer.randint(-9, 9)
    x0 = randomizer.randint(-10, 10)
    y0 = a * x0 + b
    return make_question(
        f"f(x) = {a}x + ({b}). Find f^-1({y0}) -- i.e. the x that gives this y",
        x0,
        28,
        "Swap x and y, then solve for x.",
        f"Solve {a}x + ({b}) = {y0}, giving x = {x0}.",
    )


def natural_log_evaluate() -> Question:
    x0 = randomizer.randint(1, 50)
    answer = math.log(x0)
    return make_question(
        f"ln({x0})",
        answer,
        25,
        "Use the natural logarithm (base e).",
        f"ln({x0}) \u2248 {answer:.4f}.",
    )


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def rectangle_perimeter() -> Question:
    length = randomizer.randint(2, 29)
    width = randomizer.randint(2, 29)
    answer = 2 * (length + width)
    return make_question(
        f"Perimeter of a rectangle with length {length} and width {width}",
        answer,
        15,
        "Use P = 2(l + w).",
        f"2 x ({length} + {width}) = {answer}.",
    )


def rectangle_area() -> Question:
    length = randomizer.randint(2, 29)
    width = randomizer.randint(2, 29)
    answer = length * width
    return make_question(
        f"Area of a rectangle with length {length} and width {width}",
        answer,
        15,
        "Use A = length x width.",
        f"{length} x {width} = {answer}.",
    )


def triangle_area() -> Question:
    base_length = randomizer.randint(2, 29)
    height = randomizer.randint(2, 29)
    answer = 0.5 * base_length * height
    return make_question(
        f"Area of a triangle with base {base_length} and height {height}",
        answer,
        18,
        "Use A = 1/2 x base x height.",
        f"Half of {base_length} x {height} gives the area.",
    )


def circle_area() -> Question:
    radius = randomizer.randint(2, 19)
    answer = 3.14159 * radius * radius
    return make_question(
        f"Area of a circle with radius {radius} (use pi = 3.14159)",
        answer,
        22,
        "Use A = pi x r^2.",
        f"3.14159 x {radius} x {radius} = {answer:.2f}.",
    )


def pythagorean_hypotenuse() -> Question:
    leg_a = randomizer.randint(3, 19)
    leg_b = randomizer.randint(3, 19)
    answer = math.sqrt(leg_a * leg_a + leg_b * leg_b)
    return make_question(
        f"Hypotenuse of a right triangle with legs {leg_a} and {leg_b}",
        answer,
        20,
        "Use a^2 + b^2 = c^2.",
        f"Take the square root of {leg_a}^2 + {leg_b}^2.",
    )


def rectangular_prism_volume() -> Question:
    length = randomizer.randint(2, 14)
    width = randomizer.randint(2, 14)
    height = randomizer.randint(2, 14)
    answer = length * width * height
    return make_question(
        f"Volume of a rectangular prism with length {length}, width {width}, height {height}",
        answer,
        20,
        "Use V = length x width x height.",
        f"Multiply {length} x {width} x {height}.",
    )


def circle_circumference() -> Question:
    radius = randomizer.randint(2, 14)
    answer = 2 * 3.14159 * radius
    return make_question(
        f"Circumference of a circle with radius {radius} (use pi = 3.14159)",
        answer,
        22,
        "Use C = 2 x pi x r.",
        f"2 x 3.14159 x {radius} = {answer:.2f}.",
    )


def triangle_missing_side() -> Question:
    a = randomizer.randint(3, 11)
    b = randomizer.randint(3, 11)
    c = math.sqrt(a * a + b * b)
    return make_question(
        f"A right triangle has legs {a} and {b}. Find the hypotenuse.",
        c,
        22,
        "Use Pythagoras: c = sqrt(a^2 + b^2).",
        f"sqrt({a}^2 + {b}^2) = {c:.2f}.",
    )


def surface_area_cuboid() -> Question:
    l = randomizer.randint(2, 9)
    w = randomizer.randint(2, 9)
    h = randomizer.randint(2, 9)
    answer = 2 * (l * w + l * h + w * h)
    return make_question(
        f"Surface area of a cuboid {l} x {w} x {h}",
        answer,
        28,
        "Use SA = 2(lw + lh + wh).",
        f"2 x ({l}x{w} + {l}x{h} + {w}x{h}).",
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
    return make_question(
        f"sin({angle} degrees)",
        answer,
        15,
        "Use a standard sine value.",
        f"sin({angle}) \u2248 {answer:.3f}.",
    )


def cosine_of_common_angle() -> Question:
    angle = COMMON_ANGLES[randomizer.randrange(len(COMMON_ANGLES))]
    answer = math.cos(degrees_to_radians(angle))
    return make_question(
        f"cos({angle} degrees)",
        answer,
        15,
        "Use a standard cosine value.",
        f"cos({angle}) \u2248 {answer:.3f}.",
    )


def tangent_of_common_angle() -> Question:
    valid_angles = [0, 30, 45, 60]  # 90 is undefined, excluded
    angle = valid_angles[randomizer.randrange(len(valid_angles))]
    answer = math.tan(degrees_to_radians(angle))
    return make_question(
        f"tan({angle} degrees)",
        answer,
        15,
        "Remember tan = opposite / adjacent.",
        f"tan({angle}) \u2248 {answer:.3f}.",
    )


def triangle_missing_angle() -> Question:
    angle_a = randomizer.randint(20, 99)
    angle_b = randomizer.randint(20, 149 - angle_a)
    angle_c = 180 - angle_a - angle_b
    return make_question(
        f"A triangle has angles {angle_a} and {angle_b} degrees. Find the third angle.",
        angle_c,
        15,
        "Angles in a triangle add to 180 degrees.",
        f"{angle_c} = 180 - {angle_a} - {angle_b}.",
    )


def right_triangle_opposite_side() -> Question:
    valid_angles = [30, 45, 60]
    angle = valid_angles[randomizer.randrange(len(valid_angles))]
    hypotenuse = randomizer.randint(5, 29)
    answer = hypotenuse * math.sin(degrees_to_radians(angle))
    return make_question(
        f"Right triangle with hypotenuse {hypotenuse} and angle {angle} degrees. Find the opposite side.",
        answer,
        25,
        "Use opposite = hypotenuse x sin(angle).",
        f"Multiply {hypotenuse} by sin({angle}).",
    )


def right_triangle_adjacent_side() -> Question:
    valid_angles = [30, 45, 60]
    angle = valid_angles[randomizer.randrange(len(valid_angles))]
    hypotenuse = randomizer.randint(5, 29)
    answer = hypotenuse * math.cos(degrees_to_radians(angle))
    return make_question(
        f"Right triangle with hypotenuse {hypotenuse} and angle {angle} degrees. Find the adjacent side.",
        answer,
        25,
        "Use adjacent = hypotenuse x cos(angle).",
        f"Multiply {hypotenuse} by cos({angle}).",
    )


# ---------------------------------------------------------------------------
# Combinatorics
# ---------------------------------------------------------------------------

def factorial_value() -> Question:
    n = randomizer.randint(3, 8)
    answer = math.factorial(n)
    return make_question(
        f"{n}! (factorial)",
        answer,
        15,
        "Multiply all integers from 1 to n.",
        f"{n}! = {answer}.",
    )


def permutations_count() -> Question:
    n = randomizer.randint(4, 10)
    r = randomizer.randint(2, n)
    answer = math.perm(n, r)
    return make_question(
        f"How many ways to arrange {r} items chosen from {n} distinct items (order matters)? P({n},{r})",
        answer,
        24,
        "Use P(n, r) = n! / (n - r)!.",
        f"P({n},{r}) = {answer}.",
    )


def combinations_count() -> Question:
    n = randomizer.randint(4, 12)
    r = randomizer.randint(2, n)
    answer = math.comb(n, r)
    return make_question(
        f"How many ways to choose {r} items from {n} distinct items (order doesn't matter)? C({n},{r})",
        answer,
        24,
        "Use C(n, r) = n! / (r! * (n - r)!).",
        f"C({n},{r}) = {answer}.",
    )


def coin_flip_probability() -> Question:
    n = randomizer.randint(3, 6)
    k = randomizer.randint(0, n)
    answer = round(math.comb(n, k) / (2 ** n), 4)
    return make_question(
        f"Flipping a fair coin {n} times, what is P(exactly {k} heads)? (as a decimal)",
        answer,
        32,
        "Use the binomial formula: C(n,k) / 2^n.",
        f"C({n},{k}) / 2^{n} = {answer}.",
    )


# ---------------------------------------------------------------------------
# Calculus
# ---------------------------------------------------------------------------

def derivative_of_quadratic_at_point() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-6, 6)
    c = randomizer.randint(-6, 6)
    x0 = randomizer.randint(-4, 4)
    answer = 2 * a * x0 + b
    return make_question(
        f"f(x) = {a}x^2 + ({b})x + ({c}). Find f'({x0})",
        answer,
        25,
        "Differentiate ax^2 to 2ax, and bx to b.",
        f"f'(x) = {2 * a}x + ({b}). Substitute x = {x0}.",
    )


def derivative_of_cubic_at_point() -> Question:
    a = randomizer.randint(1, 3)
    b = randomizer.randint(-4, 4)
    c = randomizer.randint(-4, 4)
    x0 = randomizer.randint(-3, 3)
    answer = 3 * a * x0 * x0 + 2 * b * x0 + c
    return make_question(
        f"f(x) = {a}x^3 + ({b})x^2 + ({c})x. Find f'({x0})",
        answer,
        30,
        "Use the power rule on each term.",
        f"Differentiate to {3 * a}x^2 + {2 * b}x + {c}.",
    )


def definite_integral_of_linear() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-5, 5)
    upper_bound = randomizer.randint(2, 7)
    answer = a / 2.0 * upper_bound * upper_bound + b * upper_bound
    return make_question(
        f"Evaluate the definite integral of ({a}x + {b}) dx from 0 to {upper_bound}",
        answer,
        30,
        "Find the antiderivative, then substitute the bounds.",
        f"The antiderivative is {a / 2.0}x^2 + {b}x.",
    )


def limit_at_infinity_ratio() -> Question:
    a = randomizer.randint(1, 8)
    b = randomizer.randint(1, 8)
    answer = a / b
    return make_question(
        f"Find the limit as x approaches infinity of ({a}x + 7) / ({b}x - 3)",
        answer,
        25,
        "Compare the coefficients of the highest powers of x.",
        f"The limit is {a}/{b}.",
    )


def limit_by_factoring() -> Question:
    p = randomizer.randint(2, 9)
    answer = 2 * p
    return make_question(
        f"Find the limit as x approaches {p} of (x^2 - {p * p}) / (x - {p})",
        answer,
        25,
        "Factor the numerator using difference of squares.",
        f"After cancelling, the expression becomes x + {p}.",
    )


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
    return make_question(
        f"f(x,y) = {a}x^2 + ({b})xy + ({c})y^2. Find the partial derivative df/dx at ({x0}, {y0})",
        answer,
        30,
        "Differentiate with respect to x, treating y as constant.",
        f"df/dx = {2 * a}x + ({b})y. At ({x0}, {y0}) = {answer}.",
    )


def partial_derivative_y_at_point() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(-5, 5)
    c = randomizer.randint(1, 5)
    x0 = randomizer.randint(-4, 4)
    y0 = randomizer.randint(-4, 4)
    # f(x, y) = a*x^2 + b*x*y + c*y^2  ->  df/dy = bx + 2cy
    answer = b * x0 + 2 * c * y0
    return make_question(
        f"f(x,y) = {a}x^2 + ({b})xy + ({c})y^2. Find the partial derivative df/dy at ({x0}, {y0})",
        answer,
        30,
        "Differentiate with respect to y, treating x as constant.",
        f"df/dy = ({b})x + {2 * c}y. At ({x0}, {y0}) = {answer}.",
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
    return make_question(
        f"f(x,y) = {a}x^2 + {b}y^2. Find the magnitude of the gradient at ({x0}, {y0})",
        answer,
        32,
        "Compute both partials, then take the Euclidean norm.",
        f"grad = ({gx}, {gy}), magnitude = {answer:.2f}.",
    )


def double_integral_over_rectangle() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(1, 5)
    x_max = randomizer.randint(2, 5)
    y_max = randomizer.randint(2, 5)
    # integral over [0, x_max] x [0, y_max] of (a*x + b*y) dA
    answer = a * (x_max ** 2) / 2 * y_max + b * (y_max ** 2) / 2 * x_max
    return make_question(
        f"Evaluate the double integral of ({a}x + {b}y) dA over the rectangle [0,{x_max}] x [0,{y_max}]",
        answer,
        40,
        "Integrate with respect to x first, then y.",
        f"Result = {a}/2 * {x_max}^2 * {y_max} + {b}/2 * {y_max}^2 * {x_max}.",
    )


def divergence_at_point() -> Question:
    a = randomizer.randint(1, 5)
    b = randomizer.randint(1, 5)
    x0 = randomizer.randint(-4, 4)
    y0 = randomizer.randint(-4, 4)
    # F(x, y) = (a*x^2, b*y^2)  ->  div F = 2ax + 2by
    answer = 2 * a * x0 + 2 * b * y0
    return make_question(
        f"Vector field F(x,y) = ({a}x^2, {b}y^2). Find the divergence of F at ({x0}, {y0})",
        answer,
        35,
        "Divergence is the sum of partial derivatives of each component.",
        f"div F = {2 * a}x + {2 * b}y. At ({x0}, {y0}) = {answer}.",
    )


# ---------------------------------------------------------------------------
# Differential Equations
# ---------------------------------------------------------------------------

def exponential_growth_at_time() -> Question:
    y0 = randomizer.randint(10, 100)
    k = randomizer.randint(1, 5) / 10.0
    t = randomizer.randint(1, 5)
    # dy/dt = k*y, y(0) = y0  ->  y(t) = y0 * e^(k*t)
    answer = y0 * math.exp(k * t)
    return make_question(
        f"dy/dt = {k}y, y(0) = {y0}. Find y({t}) (exponential growth)",
        answer,
        32,
        "Use the solution y(t) = y0 * e^(kt).",
        f"y({t}) = {y0} * e^({k} * {t}) \u2248 {answer:.2f}.",
    )


def exponential_decay_half_life() -> Question:
    initial = randomizer.randint(100, 1000)
    half_life = randomizer.randint(2, 10)
    elapsed = half_life * randomizer.randint(1, 3)
    answer = initial * (0.5 ** (elapsed / half_life))
    return make_question(
        f"A substance with half-life {half_life} years starts at {initial}g. How much remains after {elapsed} years?",
        answer,
        32,
        "Use N(t) = N0 * (1/2)^(t / half_life).",
        f"{initial} * (1/2)^({elapsed}/{half_life}) \u2248 {answer:.2f}.",
    )


def newtons_law_of_cooling() -> Question:
    t_env = randomizer.randint(15, 25)
    t0 = randomizer.randint(70, 100)
    k = randomizer.randint(1, 3) / 10.0
    t = randomizer.randint(1, 5)
    # T(t) = T_env + (T0 - T_env) * e^(-k*t)
    answer = t_env + (t0 - t_env) * math.exp(-k * t)
    return make_question(
        f"Newton's law of cooling: room temperature {t_env} degrees, object starts at {t0} degrees, "
        f"cooling constant k = {k}. Find the temperature at t = {t} (T(t) = T_env + (T0-T_env)e^(-kt))",
        answer,
        36,
        "Apply T(t) = T_env + (T0 - T_env) * e^(-kt).",
        f"T({t}) = {t_env} + ({t0} - {t_env}) * e^(-{k}*{t}) \u2248 {answer:.2f}.",
    )


def characteristic_equation_larger_root() -> Question:
    p = randomizer.randint(-8, 8)
    q = p
    while q == p:
        q = randomizer.randint(-8, 8)
    b = -(p + q)
    c = p * q
    answer = max(p, q)
    return make_question(
        f"For the ODE y'' + ({b})y' + ({c})y = 0, the characteristic equation has two real roots. Find the larger root.",
        answer,
        32,
        "Solve r^2 + br + c = 0.",
        f"The roots are {p} and {q}; the larger is {answer}.",
    )


def logistic_growth_at_time() -> Question:
    carrying_capacity = randomizer.randint(500, 1000)
    p0 = randomizer.randint(10, 50)
    r = randomizer.randint(1, 3) / 10.0
    t = randomizer.randint(1, 5)
    # P(t) = K / (1 + ((K - P0) / P0) * e^(-r*t))
    answer = carrying_capacity / (1 + ((carrying_capacity - p0) / p0) * math.exp(-r * t))
    return make_question(
        f"Logistic growth: carrying capacity {carrying_capacity}, P(0) = {p0}, growth rate r = {r}. Find P({t}).",
        answer,
        40,
        "Use P(t) = K / (1 + ((K - P0) / P0) * e^(-rt)).",
        f"P({t}) \u2248 {answer:.2f}.",
    )


# ---------------------------------------------------------------------------
# Linear Algebra
# ---------------------------------------------------------------------------

def vector_addition_component() -> Question:
    a1 = randomizer.randint(-10, 10)
    a2 = randomizer.randint(-10, 10)
    b1 = randomizer.randint(-10, 10)
    b2 = randomizer.randint(-10, 10)
    return make_question(
        f"u = ({a1}, {a2}), v = ({b1}, {b2}). Find the x-component of u + v",
        a1 + b1,
        18,
        "Add the first components.",
        f"{a1} + {b1} = {a1 + b1}.",
    )


def vector_dot_product_2d() -> Question:
    a1 = randomizer.randint(-10, 10)
    a2 = randomizer.randint(-10, 10)
    b1 = randomizer.randint(-10, 10)
    b2 = randomizer.randint(-10, 10)
    answer = a1 * b1 + a2 * b2
    return make_question(
        f"u = ({a1}, {a2}), v = ({b1}, {b2}). Find u . v (dot product)",
        answer,
        20,
        "Multiply corresponding components and add them.",
        f"Calculate ({a1} x {b1}) + ({a2} x {b2}).",
    )


def vector_magnitude_2d() -> Question:
    a1 = randomizer.randint(-12, 12)
    a2 = randomizer.randint(-12, 12)
    answer = math.sqrt(a1 * a1 + a2 * a2)
    return make_question(
        f"Find the magnitude of vector u = ({a1}, {a2})",
        answer,
        22,
        "Use sqrt(x^2 + y^2).",
        f"Calculate sqrt({a1}^2 + {a2}^2).",
    )


def matrix_determinant_2x2() -> Question:
    a = randomizer.randint(-8, 8)
    b = randomizer.randint(-8, 8)
    c = randomizer.randint(-8, 8)
    d = randomizer.randint(-8, 8)
    answer = a * d - b * c
    return make_question(
        f"Determinant of matrix [[{a}, {b}], [{c}, {d}]]",
        answer,
        25,
        "For a 2x2 matrix use ad - bc.",
        f"Calculate ({a} x {d}) - ({b} x {c}).",
    )


def matrix_addition_entry() -> Question:
    a11 = randomizer.randint(-9, 9)
    a12 = randomizer.randint(-9, 9)
    b11 = randomizer.randint(-9, 9)
    b12 = randomizer.randint(-9, 9)
    return make_question(
        f"A = [[{a11}, {a12}], [.., ..]], B = [[{b11}, {b12}], [.., ..]]. Find entry (1,1) of A + B",
        a11 + b11,
        20,
        "Add the matching entries.",
        f"The (1,1) entry is {a11} + {b11}.",
    )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def generate_small_data_set(count: int, min_value: int, max_value: int) -> List[int]:
    return [randomizer.randint(min_value, max_value) for _ in range(count)]


def mean_of_list() -> Question:
    data = generate_small_data_set(5, 1, 50)
    total = sum(data)
    answer = total / len(data)
    data_str = ", ".join(str(v) for v in data)
    return make_question(
        f"Mean of {{{data_str}}}",
        answer,
        25,
        "Add all values and divide by the number of values.",
        f"The total is {total} and there are {len(data)} values.",
    )


def range_of_list() -> Question:
    data = generate_small_data_set(5, 1, 50)
    min_val = min(data)
    max_val = max(data)
    answer = max_val - min_val
    data_str = ", ".join(str(v) for v in data)
    return make_question(
        f"Range of {{{data_str}}}",
        answer,
        20,
        "Range = maximum - minimum.",
        f"{max_val} - {min_val} = {answer}.",
    )


def median_of_list() -> Question:
    data = generate_small_data_set(5, 1, 50)  # Odd count keeps the median a single value
    sorted_data = sorted(data)
    answer = sorted_data[len(sorted_data) // 2]
    data_str = ", ".join(str(v) for v in data)
    return make_question(
        f"Median of {{{data_str}}}",
        answer,
        25,
        "Sort the values and choose the middle value.",
        f"Sorted values: {', '.join(str(v) for v in sorted_data)}.",
    )


def simple_probability() -> Question:
    threshold = randomizer.randint(1, 5)  # 1 to 5
    favorable = 6 - threshold  # Outcomes on a six-sided die greater than the threshold
    answer = round(favorable / 6, 3)
    return make_question(
        f"Rolling a fair six-sided die, what is P(roll > {threshold})? (as a decimal)",
        answer,
        20,
        "Count the favourable outcomes and divide by 6.",
        f"There are {favorable} favourable outcomes out of 6.",
    )


def mode_of_list() -> Question:
    data = generate_small_data_set(7, 1, 6)
    # Force a repeated value so a mode always exists.
    mode = randomizer.randint(1, 6)
    data[0] = mode
    data[1] = mode
    data[2] = mode
    answer = mode
    data_str = ", ".join(str(v) for v in data)
    return make_question(
        f"Find the mode of {{{data_str}}}",
        answer,
        25,
        "The mode is the value that appears most often.",
        f"The value {mode} appears more often than the others.",
    )


def probability_as_percentage() -> Question:
    favourable = randomizer.randint(1, 9)
    total = 10
    answer = favourable * 10
    return make_question(
        f"A probability is {favourable}/{total}. Express it as a percentage.",
        answer,
        18,
        "Multiply the decimal probability by 100.",
        f"{favourable}/{total} = {answer}%.",
    )


# ---------------------------------------------------------------------------
# Complex Numbers
# ---------------------------------------------------------------------------

def complex_addition_component() -> Question:
    a1 = randomizer.randint(-10, 10)
    b1 = randomizer.randint(-10, 10)
    a2 = randomizer.randint(-10, 10)
    b2 = randomizer.randint(-10, 10)
    return make_question(
        f"z1 = {a1} + {b1}i, z2 = {a2} + {b2}i. Find the real part of z1 + z2",
        a1 + a2,
        18,
        "Add the real parts together.",
        f"{a1} + {a2} = {a1 + a2}.",
    )


def complex_modulus() -> Question:
    a = randomizer.randint(-12, 12)
    b = randomizer.randint(-12, 12)
    answer = math.sqrt(a * a + b * b)
    return make_question(
        f"Find the modulus |z| of z = {a} + {b}i",
        answer,
        22,
        "Use |z| = sqrt(a^2 + b^2).",
        f"sqrt({a}^2 + {b}^2) = {answer:.2f}.",
    )


def complex_multiplication_component() -> Question:
    a1 = randomizer.randint(-9, 9)
    b1 = randomizer.randint(-9, 9)
    a2 = randomizer.randint(-9, 9)
    b2 = randomizer.randint(-9, 9)
    # (a1 + b1 i)(a2 + b2 i) = (a1*a2 - b1*b2) + (a1*b2 + a2*b1) i
    real = a1 * a2 - b1 * b2
    return make_question(
        f"z1 = {a1} + {b1}i, z2 = {a2} + {b2}i. Find the real part of z1 * z2",
        real,
        28,
        "Use FOIL: real part = a1*a2 - b1*b2.",
        f"({a1} x {a2}) - ({b1} x {b2}) = {real}.",
    )


def complex_conjugate_modulus_squared() -> Question:
    a = randomizer.randint(-10, 10)
    b = randomizer.randint(-10, 10)
    answer = a * a + b * b
    return make_question(
        f"z = {a} + {b}i. Find z times its complex conjugate (a real number)",
        answer,
        28,
        "z * conj(z) = a^2 + b^2.",
        f"{a}^2 + {b}^2 = {answer}.",
    )


def complex_power_de_moivre() -> Question:
    r = randomizer.randint(1, 4)
    angle_deg = randomizer.choice([0, 30, 45, 60, 90])
    n = randomizer.randint(2, 4)
    theta = math.radians(angle_deg)
    # De Moivre's theorem: z^n = r^n * (cos(n*theta) + i*sin(n*theta))
    answer = (r ** n) * math.cos(n * theta)
    return make_question(
        f"z has modulus {r} and argument {angle_deg} degrees. Find the real part of z^{n} (De Moivre's theorem)",
        answer,
        38,
        "Use r^n * cos(n*theta).",
        f"Real part = {r}^{n} * cos({n} * {angle_deg}deg) \u2248 {answer:.3f}.",
    )


# ---------------------------------------------------------------------------
# Sequences & Series
# ---------------------------------------------------------------------------

def arithmetic_sequence_nth_term() -> Question:
    a1 = randomizer.randint(1, 20)
    d = randomizer.randint(-5, 5)
    n = randomizer.randint(5, 20)
    answer = a1 + (n - 1) * d
    return make_question(
        f"Arithmetic sequence: a1 = {a1}, common difference {d}. Find a{n}",
        answer,
        20,
        "Use a_n = a1 + (n - 1) * d.",
        f"{a1} + ({n - 1}) * {d} = {answer}.",
    )


def geometric_sequence_nth_term() -> Question:
    a1 = randomizer.randint(1, 5)
    r = randomizer.randint(2, 4)
    n = randomizer.randint(3, 7)
    answer = a1 * (r ** (n - 1))
    return make_question(
        f"Geometric sequence: a1 = {a1}, common ratio {r}. Find a{n}",
        answer,
        24,
        "Use a_n = a1 * r^(n-1).",
        f"{a1} * {r}^{n - 1} = {answer}.",
    )


def arithmetic_series_sum() -> Question:
    a1 = randomizer.randint(1, 20)
    d = randomizer.randint(1, 6)
    n = randomizer.randint(5, 15)
    answer = n / 2 * (2 * a1 + (n - 1) * d)
    return make_question(
        f"Sum of the first {n} terms of an arithmetic sequence with a1 = {a1} and common difference {d}",
        answer,
        28,
        "Use S_n = n/2 * (2*a1 + (n-1)*d).",
        f"{n}/2 * (2*{a1} + {n-1}*{d}) = {answer}.",
    )


def geometric_series_sum() -> Question:
    a1 = randomizer.randint(1, 5)
    r = randomizer.randint(2, 3)
    n = randomizer.randint(3, 6)
    answer = a1 * (r ** n - 1) / (r - 1)
    return make_question(
        f"Sum of the first {n} terms of a geometric sequence with a1 = {a1} and common ratio {r}",
        answer,
        30,
        "Use S_n = a1 * (r^n - 1) / (r - 1).",
        f"{a1} * ({r}^{n} - 1) / ({r} - 1) = {answer}.",
    )


def infinite_geometric_series_sum() -> Question:
    a1 = randomizer.randint(1, 10)
    denominator = randomizer.randint(2, 5)  # ratio r = 1 / denominator, so |r| < 1 and the series converges
    r = 1 / denominator
    answer = a1 / (1 - r)
    return make_question(
        f"Sum to infinity of a geometric series with a1 = {a1} and common ratio 1/{denominator}",
        answer,
        32,
        "Use S = a1 / (1 - r) when |r| < 1.",
        f"{a1} / (1 - 1/{denominator}) = {answer:.2f}.",
    )


# ---------------------------------------------------------------------------
# Output formatting and parsing helpers
# ---------------------------------------------------------------------------

def format_answer(value: float) -> str:
    """Formats an answer for display, dropping unnecessary decimal zeros."""
    if abs(value - round(value)) < 0.000001:
        return f"{value:.0f}"
    return f"{value:.3f}"


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


def clear_screen() -> None:
    """Clears the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


# ---------------------------------------------------------------------------
# Question factory helper
# ---------------------------------------------------------------------------

def make_question(
    prompt: str,
    answer: float,
    time_limit: int,
    hint: str = "",
    explanation: str = "",
    tolerance: float = 0.05,
) -> Question:
    """Creates a Question with computed points based on the time limit."""
    return Question(
        prompt=prompt,
        answer=answer,
        tolerance=tolerance,
        time_limit_seconds=time_limit,
        hint=hint,
        explanation=explanation,
        points=calculate_base_points(time_limit),
    )


def calculate_base_points(time_limit: int) -> int:
    """Determines base points from the time limit (tighter time = higher points)."""
    if time_limit <= 15:
        return 100
    if time_limit <= 20:
        return 125
    if time_limit <= 25:
        return 150
    return 175


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
    "order_of_operations": order_of_operations,
    "fraction_addition": fraction_addition,
    "ratio_question": ratio_question,
    "square_root_question": square_root_question,
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
    "expand_brackets": expand_brackets,
    "factorise_quadratic": factorise_quadratic,
    "solve_quadratic": solve_quadratic,
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
    "circle_circumference": circle_circumference,
    "triangle_missing_side": triangle_missing_side,
    "surface_area_cuboid": surface_area_cuboid,
    # Trigonometry
    "sine_of_common_angle": sine_of_common_angle,
    "cosine_of_common_angle": cosine_of_common_angle,
    "tangent_of_common_angle": tangent_of_common_angle,
    "triangle_missing_angle": triangle_missing_angle,
    "right_triangle_opposite_side": right_triangle_opposite_side,
    "right_triangle_adjacent_side": right_triangle_adjacent_side,
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
    "mode_of_list": mode_of_list,
    "probability_as_percentage": probability_as_percentage,
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
