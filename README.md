Math Quiz — Python Edition: Code Documentation
A section-by-section walkthrough of math_quiz.py, a Python port of the original C# console application.

1. Overview
This is a single-file Python console application (math_quiz.py) that generates randomized, timed math questions across seven topics — Arithmetic, Algebra, Geometry, Trigonometry, Calculus, Linear Algebra, and Statistics — with difficulty that increases as the player progresses through a round.
It is a direct, function-for-function port of the original C# version (Program.cs). The public behavior — every prompt, every formula, every difficulty curve, every edge case — is unchanged; what's different is purely how those ideas are expressed in idiomatic Python: class Question with typed fields becomes a @dataclass, C# Func<Question> delegates become plain Python callables (functions and lambdas), and Dictionary<string, List<Func<Question>>> becomes a Python dict[str, list[Callable[[], Question]]].
It is entirely platform-independent: it uses only the Python standard library (random, math, time, dataclasses, typing) for I/O and math, so it runs identically on Windows, macOS, and Linux with any Python 3.9+ interpreter — no pip install, no virtual environment, and no external packages are required.
The program has no external dependencies, no UI framework, and no persistence — everything lives in memory for the duration of a single run, exactly as in the original.

2. High-Level Architecture
The code is organized into one data structure and a set of module-level functions inside math_quiz.py:
●	Question — a @dataclass, Python's built-in tool for plain data containers (the equivalent of a C# DTO), representing one generated question.
●	main(), run_quiz(), generate_question(), and friends — ordinary module-level functions holding all program logic: I/O, control flow, difficulty scaling, and every individual question generator. Python has no requirement to wrap these in a class the way C# requires a containing type (Program), so they live directly at module scope.
As in the original, there is no object-oriented modeling of "topics" as classes — instead, topics are represented as a Dict[str, List[Callable[[], Question]]], which remains the structural core of the whole design (explained in detail in Section 5).
2.1 The Question dataclass
@dataclass
class Question:
    prompt: str
    answer: float
    tolerance: float
    time_limit_seconds: int
Every question generator function, regardless of topic, returns one of these. The @dataclass decorator auto-generates __init__, __repr__, and __eq__ from the type-annotated fields — the Python idiom for exactly what the C# version's plain field-only class was doing manually. This is the key abstraction that lets wildly different math domains (arithmetic, calculus, statistics) share one grading and timing pipeline:
●	prompt — the exact string shown to the player. Since it's just free text, prompts can represent anything printable: "7 + 12", "f(x) = 3x^2 + 2x. Find f'(1)", "Determinant of matrix [[2, 5], [1, 3]]".
●	answer — the correct answer, always stored as a float, even for problems that are conceptually integer-valued (e.g., matrix determinants). This uniformity is what allows one comparison routine to grade every topic.
●	tolerance — the allowed absolute error margin when comparing the player's answer to answer. This exists because many topics (circle area, trigonometric ratios, square roots, probabilities) have irrational or rounded correct answers that can't be typed exactly.
●	time_limit_seconds — a per-question time budget. Harder or more calculation-heavy question types are given more time (e.g., a matrix determinant gets 25 seconds; a single-digit addition gets 12).

3. Program Entry Point and Main Loop
def main() -> None:
    ...
    play_again = True
    while play_again:
        category = ask_for_category()
        question_count = ask_for_question_count()
        run_quiz(category, question_count)
        ...
        play_again = response is not None and response.strip().lower().startswith("y")
Just as in the C# version, main() is intentionally thin. It only orchestrates three things per round: ask which topic, ask how many questions, run the quiz. The play_again loop means the whole program is really a loop of independent "rounds," each of which can use a different topic and length — state does not persist between rounds (score is local to run_quiz).
The program is launched via the standard Python guard at the bottom of the file:
if __name__ == "__main__":
    main()
This is Python's idiom for "only run this when the file is executed directly, not when it's imported as a module" — there is no direct C# equivalent, since C#'s Main() is always the designated entry point of the assembly rather than something inferred from how the file is invoked.
3.1 Input collection helpers
ask_for_category() and ask_for_question_count() both follow the same defensive pattern: read a raw string with input(), attempt to parse it, and silently fall back to a sensible default if parsing fails or the value is out of range.
●	Python's built-in int() and float() raise a ValueError on bad input rather than returning a success flag the way C#'s int.TryParse does. To keep the same "never crash, just fall back" behavior, this port wraps them in small helpers, try_parse_int() and try_parse_float() (Section 8), which catch the exception and return None instead — the Python equivalent of a failed TryParse.
●	ask_for_category() builds a numbered menu on the fly from categories.keys(), so adding or removing a topic from the dictionary automatically updates the menu — no hardcoded menu text to keep in sync. (Python dicts preserve insertion order, exactly like .NET's Dictionary<TKey, TValue>, so the menu order matches the order topics were added in build_categories().)
●	If the player's input doesn't parse to a valid menu number, the function returns "Mixed" rather than erroring or looping — this is a deliberate choice, carried over unchanged, to keep the console experience friction-free (bad input never crashes or blocks the program).
●	ask_for_question_count() defaults to 10 under the same philosophy.

4. The Quiz Loop and Grading Logic (run_quiz)
This is the core gameplay loop. For each of question_count iterations:
progress = 1.0 if question_count <= 1 else i / (question_count - 1)
question = generate_question(category, progress)
progress is a normalized value from 0.0 (first question) to 1.0 (last question), computed from the current index i. This is the single variable that drives difficulty scaling — it's passed into generate_question, which uses it to decide how hard a question should be (see Section 5.2). Python 3's / operator always performs true (float) division — unlike C#'s / on two ints, which would floor-divide — so, unlike the C# version, this line needs no explicit (double) cast to avoid integer division. The guard for question_count <= 1 still avoids a divide-by-zero when there's only one question.
4.1 Timing a single question
start_time = time.perf_counter()
raw_answer = input(f"[{question.time_limit_seconds}s allowed] {question.prompt} = ")
elapsed_seconds = time.perf_counter() - start_time
time.perf_counter() is Python's equivalent of C#'s System.Diagnostics.Stopwatch — it's a monotonic, high-resolution clock intended exactly for measuring short elapsed durations, and it isn't affected by system clock adjustments the way time.time() can be. It's read immediately before the prompt is printed and again immediately after input() returns — so the elapsed time captures exactly the wall-clock time the player spent reading and answering, including their typing time, identically to the C# version.
This is the same deliberate architectural trade-off carried over from the original: input() is a blocking call. There's no reliable, cross-platform way to force it to return early once a time limit expires without spawning a background thread (or using platform-specific, non-portable tricks like select() on stdin, which doesn't work uniformly across Windows and POSIX systems) and risking orphaned threads that "leak" into the next read call. Rather than build that fragile mechanism, the program takes the simpler and more robust approach of measuring elapsed time after the fact and grading accordingly. The player always sees their allotted time up front, but the enforcement is "honesty-based" from the console's perspective — a deliberate, documented trade-off rather than a bug.
4.2 Grading
within_time = elapsed_seconds <= question.time_limit_seconds
user_answer = try_parse_float(raw_answer)
parsed = user_answer is not None
is_correct = (
    within_time
    and parsed
    and abs(user_answer - question.answer) <= question.tolerance
)
Three independent checks must all pass for a question to count as correct — unchanged from the original:
●	within_time — the elapsed-time reading didn't exceed the question's budget.
●	parsed — the raw input string is a valid floating-point number. Python's built-in float() already behaves like C#'s NumberStyles.Float with CultureInfo.InvariantCulture: it always expects a period as the decimal separator and standard formats like 12.5 or -3, regardless of the host machine's regional settings. Unlike C#'s double.Parse, Python's float() is never locale-sensitive by default, so no extra configuration is needed to get this cross-platform guarantee — it's the library default rather than something that has to be explicitly requested.
●	The tolerance check — abs(user_answer - question.answer) <= question.tolerance — is a standard epsilon comparison, necessary because floating-point values (and real-world rounded answers like 0.333 for a fraction) should never be compared with exact equality (==).
If any check fails, the player is told the correct answer (formatted via format_answer, see Section 8) and a summary line is appended to missed_summaries, which is printed as a review list at the end of the round.

5. Difficulty Scaling and Topic Selection (generate_question)
This remains the most architecturally interesting part of the program — the mechanism that unifies "pick a topic" and "make it get harder" into one small function.
5.1 Topic pools as ordered lists of generator functions
categories: Dict[str, List[Callable[[], Question]]] = build_categories()
Each topic (e.g., "Algebra") maps to a List[Callable[[], Question]] — an ordered list of zero-argument callables, each of which, when invoked, returns a freshly randomized Question. Critically, the list order encodes difficulty: index 0 is the easiest generator in that topic, and the last index is the hardest. For example, in Algebra:
category_map["Algebra"] = [
    solve_addition_one_step,       # index 0 -- easiest
    solve_multiplication_one_step,
    solve_two_step_linear,
    evaluate_expression,
    quadratic_larger_root,
    linear_system_solve_x,         # index 5 -- hardest
]
This is a form of the Strategy pattern: instead of a big if/elif chain choosing behavior, behavior is represented as data (a list of function references) that can be indexed, sliced, and iterated like any other collection. It's also why adding a new question type to a topic is a one-line change — write the generator function, add it to the list at the position matching its difficulty.
Note the two syntaxes used when populating these lists, mirroring the two syntaxes the C# version used for the same reason:
●	solve_addition_one_step (a bare function reference — Python functions are first-class objects, so naming a function without calling it, i.e. without trailing parentheses, passes the function itself; this is the direct equivalent of a C# method group).
●	lambda: whole_addition(1, 20) (a lambda expression — needed here because whole_addition takes parameters, so the lambda "bakes in" fixed arguments and exposes a zero-argument closure that fits the Callable[[], Question] shape; this is the direct equivalent of the C# () => WholeAddition(1, 20) lambda).
5.2 Mapping progress to a difficulty index
def generate_question(category: str, progress: float) -> Question:
    if category == "Mixed":
        real_categories = list(categories.keys())
        pool = categories[real_categories[randomizer.randrange(len(real_categories))]]
    else:
        pool = categories[category]

    target_index = round(progress * (len(pool) - 1))
    window_start = max(0, target_index - 1)
    chosen_index = randomizer.randint(window_start, target_index)

    return pool[chosen_index]()
Walking through this — the logic is identical to the C# version, step for step:
●	Topic resolution. If the player chose "Mixed", a topic is picked uniformly at random for this single question from all keys in categories. This means in Mixed mode, difficulty still scales — but scales independently within whichever topic happens to be picked that round, rather than trying to maintain some unified cross-topic difficulty ranking (which wouldn't make sense, since "hard calculus" and "hard arithmetic" aren't comparable).
●	Target index calculation. progress * (len(pool) - 1) linearly maps the [0.0, 1.0] progress value onto the valid index range of the topic's list ([0, len(pool) - 1]). Python's built-in round() converts that to the nearest integer index. Notably, Python's round() uses the exact same rounding rule as C#'s Math.Round default — both use round-half-to-even ("banker's rounding") for values exactly halfway between two integers — so this port reproduces the original's rounding behavior exactly, including on ties, with no extra configuration needed.
●	The "sliding window." Rather than deterministically returning pool[target_index] every time, the code computes a small window [window_start, target_index] — either one or two indices wide — and picks randomly within it via randomizer.randint(window_start, target_index). window_start is clamped to 0 with max() to avoid a negative index on the very first question. Note that Python's random.randint(a, b) is inclusive of both endpoints — the same inclusive range C#'s randomizer.Next(windowStart, targetIndex + 1) achieves by adding 1 to its (exclusive) upper bound, so both versions select from exactly the same set of indices. This means the ceiling of difficulty rises deterministically and monotonically as progress increases, but there's still variety — the player might see the current difficulty tier or the one just below it, rather than a perfectly rigid, predictable staircase.
●	Invocation. pool[chosen_index]() — the extra () at the end calls the selected callable, actually generating a new randomized question at that moment (as opposed to returning a cached one), exactly as in C#.

6. Category Construction (build_categories)
build_categories() runs exactly once, at module import time (categories = build_categories(), at the bottom of the module), and returns the fully populated dictionary described above. Like the C# static field initializer it replaces, this happens once, ever, for the whole program's lifetime — module-level code in Python executes a single time on first import, and re-importing an already-loaded module reuses the cached module object rather than re-running its top-level statements.
It is a straightforward builder function — there's no dynamic discovery or reflection involved; every topic and every generator reference is explicitly listed. This keeps the program's behavior fully predictable and easy to extend by hand, at the cost of needing a code change (rather than a config change) to add new topics.
The seven topics, and the mathematical logic behind their hardest and most notable generators, are detailed below.

7. Topic-by-Topic Generator Logic
Every generator function follows the same shape: randomize some inputs within a chosen numeric range, compute the exact correct answer using the same formula a person would use by hand, build a human-readable prompt string via an f-string, and return a Question. This shape, and every formula used, is unchanged from the C# version. A representative and a non-trivial example from each topic are explained below; the remaining generators follow the same pattern.
7.1 Arithmetic
Nothing conceptually new here beyond straightforward operations, but two generators are worth noting for how they guarantee clean results:
●	whole_division picks a divisor and quotient first, then computes dividend = divisor * quotient. This guarantees the division always comes out to a whole number — the alternative (picking two arbitrary numbers and dividing) would usually produce a repeating decimal, which is undesirable for a "whole number" tier.
●	fraction_of_number uses the same trick: it picks a denominator and a multiplier, then sets whole = denominator * multiplier, guaranteeing numerator / denominator * whole is always an integer-valued float.
7.2 Algebra
●	quadratic_larger_root is the standout generator here. Rather than expanding a quadratic into ax² + bx + c form (which would require careful sign-formatting logic to display coefficients like -3 cleanly, and would require the solver to actually factor or use the quadratic formula), it exploits the zero-product property directly: it generates two distinct integer roots p and q, and presents the already-factored equation (x - p)(x - q) = 0. The correct answer is simply max(p, q). This sidesteps an entire class of string-formatting and ambiguity problems (a quadratic has two roots; asking for "the larger one" makes the expected answer unambiguous) while still testing the same underlying algebraic concept. Where C# used a do { ... } while (q == p) loop to guarantee distinct roots, Python expresses the identical retry logic as a while q == p: loop seeded with q = p before the loop, since Python has no built-in post-condition loop construct.
●	linear_system_solve_x generates a solvable 2×2 system of linear equations by working backwards: it first picks the intended solution (x0, y0), then randomly generates coefficients a1, b1, a2, b2 for two equations, rejecting any coefficient combination whose determinant (a1*b2 - a2*b1) is zero (a while determinant == 0: loop retries until a non-degenerate system is found — a zero determinant means the two equations are parallel/dependent and have no unique solution). It then back-calculates c1 = a1*x0 + b1*y0 and c2 = a2*x0 + b2*y0 so that (x0, y0) is guaranteed to satisfy both equations exactly.
7.3 Geometry
Standard formulas (perimeter 2(l+w), rectangle area l×w, triangle area 0.5×b×h, circle area πr², prism volume l×w×h) computed directly via math.pi and simple arithmetic — Python's math module standing in for C#'s System.Math. pythagorean_hypotenuse uses math.sqrt(leg_a**2 + leg_b**2) directly — since the legs are arbitrary random integers, the hypotenuse is very often irrational, which is exactly why this generator has a wider tolerance (0.05) than the exact-integer geometry generators.
7.4 Trigonometry
All angle-based generators work in degrees for the prompt text (more intuitive for a player) but must convert to radians for computation, since math.sin, math.cos, and math.tan all expect radians, exactly like their C# Math.Sin/Math.Cos/Math.Tan counterparts. This is handled by a small shared helper:
def degrees_to_radians(degrees: float) -> float:
    return degrees * math.pi / 180.0
tangent_of_common_angle deliberately uses a separate, shorter angle list ([0, 30, 45, 60]) than sine and cosine (COMMON_ANGLES = [0, 30, 45, 60, 90]), explicitly excluding 90° — since tangent is mathematically undefined at 90° (division by cos(90°) = 0), including it would return a meaningless huge floating-point number rather than throwing (Python's math.tan doesn't raise on this input any more than C#'s Math.Tan does).
triangle_missing_angle generates two angles whose sum is guaranteed to leave a valid positive third angle: angle_b is bounded above by 149 - angle_a (since angle_a itself is capped at 99°, this guarantees angle_a + angle_b < 180, leaving a positive remainder for angle_c = 180 - angle_a - angle_b).
7.5 Calculus
This is the most mathematically dense topic, and it sidesteps a hard problem: checking symbolic/algebraic answers is very difficult in code (it would require a full expression parser and a computer algebra system to verify something like "is 6x + 2 an acceptable way of writing the derivative?"). Every calculus generator instead asks the player to evaluate the result at a specific point, collapsing the correct answer down to a single number — consistent with the rest of the program's grading model, unchanged from the original.
●	derivative_of_quadratic_at_point and derivative_of_cubic_at_point apply the power rule directly in code. For f(x) = ax² + bx + c, the derivative is f'(x) = 2ax + b — the generator computes this symbolically (i.e., it knows the derivative formula, it doesn't differentiate at runtime) and evaluates it at a random x0. The cubic version follows the same idea one degree higher: f(x) = ax³ + bx² + cx → f'(x) = 3ax² + 2bx + c.
●	definite_integral_of_linear similarly hardcodes the antiderivative of a linear function: the antiderivative of ax + b is (a/2)x² + bx, evaluated at the upper bound minus at 0 (i.e., the Fundamental Theorem of Calculus, computed directly since the lower bound is fixed at 0).
●	limit_at_infinity_ratio encodes a standard calculus shortcut: for a limit of the form (ax + 7)/(bx - 3) as x → ∞, the lower-order terms (+7, -3) become negligible, and the limit equals the ratio of the leading coefficients, a/b. No actual limit-taking or infinite computation happens — the code directly computes a / b (true division, same reasoning as Section 4).
●	limit_by_factoring encodes the classic "removable discontinuity" limit: (x² - p²)/(x - p) as x → p. Algebraically, x² - p² factors as (x-p)(x+p), so the expression simplifies to x + p everywhere except at the removed point x = p, giving a limit of 2p. The code again computes this closed-form result directly rather than performing any numerical limit approximation.
7.6 Linear Algebra
Vector and matrix generators ask for a single scalar output derived from a vector/matrix operation — a component of a sum, a dot product, a magnitude, a determinant, or one entry of a matrix sum — rather than asking the player to report an entire vector or matrix (which single-value tolerance-based grading can't represent). For example, matrix_determinant_2x2 computes the standard 2×2 determinant formula a×d - b×c directly and displays the matrix using a nested-list-literal-style string: [[a, b], [c, d]].
matrix_addition_entry intentionally displays only the entries relevant to the asked-for result (using .. placeholders for the untested entries), keeping the prompt honest about what's actually being graded — the player is only ever asked to compute entry (1,1) of A + B, so only that entry's inputs are meaningfully shown.
7.7 Statistics
mean_of_list, range_of_list, and median_of_list all build on a shared helper:
def generate_small_data_set(count: int, min_value: int, max_value: int) -> List[int]:
    return [randomizer.randint(min_value, max_value) for _ in range(count)]
This is written as a Python list comprehension — the idiomatic replacement for the C# version's explicit for loop that filled an array index by index; both produce the same list of count independently random integers.
median_of_list specifically uses a fixed odd count (5) so the median is always a single middle value after sorting (Python's built-in sorted(), the equivalent of C#'s Array.Sort), avoiding the more complex "average the two middle values" logic required for even-sized data sets. simple_probability computes classic favorable-outcomes-over-total-outcomes probability for a six-sided die (P(roll > threshold) = (6 - threshold) / 6), rounded to three decimal places, graded with a small tolerance to allow for reasonable decimal rounding by the player.

8. Output Formatting and Input Parsing Helpers
def format_answer(value: float) -> str:
    if value == math.floor(value):
        return f"{value:.0f}"
    return f"{value:.3f}".rstrip("0").rstrip(".")
This small utility avoids showing ugly trailing zeros or long floating-point artifacts when revealing correct answers, matching the C# version's value.ToString("0.###") behavior exactly. If a float is a whole number (e.g., 15.0), it's displayed as "15" rather than "15.0" or "15.000". Otherwise, Python has no single built-in format specifier equivalent to C#'s "0.###" (which rounds to at most three decimal places and drops trailing zeros), so this port reproduces it in two steps: format to exactly three decimal places with f"{value:.3f}", then strip trailing zeros and, if nothing but zeros remain after the decimal point, strip the trailing decimal point itself. The net effect — at most three decimal digits, no trailing zeros — is identical to the original in every case.
def try_parse_int(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None
These two helpers (try_parse_int and its try_parse_float counterpart) are the one piece of scaffolding this port adds that has no direct line-for-line counterpart in the C# source. They exist purely to bridge an API difference: C#'s double.TryParse return a boolean success flag and hand the parsed value back through an out parameter, so a failed parse never raises. Python's int()/float() instead raise ValueError on bad input. Wrapping them in a try/except that returns None on failure reproduces the exact same "never crash, tell me if it worked" contract the rest of the program's control flow was written against — every call site checks is not None the same way the original checked the out bool result.

9. Design Principles Summary
A few cross-cutting decisions define the shape of this codebase — all of them preserved unchanged from the original C# version, since a port's job is to change the language, not the design:
●	Uniform grading via a single numeric answer. Every topic, no matter how different conceptually, is reduced to "generate a prompt, compute one correct float, compare with a tolerance." This is what allows seven unrelated math domains to share one run_quiz loop instead of needing topic-specific grading code.
●	Difficulty as data, not logic. Difficulty tiers are expressed purely through the position of a generator function in a list, and progression through those tiers is a single interpolation formula (Section 5.2) applied uniformly across every topic — no topic needs its own custom difficulty-scaling code.
●	Guaranteed-clean answers wherever possible. Many generators (whole_division, fraction_of_number, linear_system_solve_x) generate the answer first and work backwards to construct a question that produces it, rather than generating random inputs and hoping the result is clean. This avoids ugly repeating decimals or unsolvable systems without needing post-hoc validation or retry loops (except where a retry loop is unavoidable, as in the determinant-zero case).
●	Symbolic math is avoided entirely. Every calculus and algebra generator "knows" the closed-form answer to its own construction in advance (e.g., a quadratic generator that builds a polynomial from its own roots) rather than attempting to parse, solve, or symbolically manipulate expressions at runtime. This keeps the program free of any computer-algebra dependency while still covering real calculus and algebra concepts.
●	Cross-platform by construction. No OS-specific APIs and no third-party packages — the entire program depends only on the Python standard library, and float()'s locale-independence removes the need for anything like C#'s explicit CultureInfo.InvariantCulture, satisfying the original requirement that it run identically on Windows, macOS, and Linux.
●	Idiomatic translation, not literal transliteration. Where Python has a more natural way to express something — dataclasses instead of a bare-field class, list comprehensions instead of index-filling loops, try/except instead of TryParse — this port uses it, while keeping every formula, every random-range boundary, and every piece of program behavior identical to the source.

10. Step-by-Step: Getting It Running
This section walks through everything needed to go from a blank machine to a running quiz, in full detail, for macOS, Windows, and Linux. If you already have Python 3 installed, skip to Step 3.
Step 1 — Check whether Python 3 is already installed
Open a terminal (macOS: Terminal or iTerm; Windows: Command Prompt, PowerShell, or the terminal inside VS Code; Linux: your distribution's terminal) and run:
python3 --version
On Windows, if that command isn't recognized, also try:
py --version
●	If this prints a version number of 3.9 or higher (e.g. "Python 3.12.4"), Python is already installed — skip ahead to Step 3.
●	If you see an error like "command not found: python3" or "'python3' is not recognized", Python isn't installed yet (or isn't on your PATH) — continue to Step 2.
This project uses f-strings, type hints, and dataclasses, all of which require Python 3.7 or newer; 3.9+ is recommended and is what current python.org installers provide by default.
Step 2 — Install Python 3
On macOS:
●	Go to https://www.python.org/downloads/ in your browser.
●	Download the latest "macOS 64-bit universal2 installer".
●	Open the downloaded .pkg file and follow the installer prompts (Continue → Agree → Install). You may be asked for your Mac login password, since it installs system-wide.
●	Once finished, close and reopen your terminal window, then confirm with python3 --version.
On Windows:
●	Go to https://www.python.org/downloads/ in your browser and download the latest Windows installer.
●	Run the downloaded .exe installer. On the very first screen, check the box labeled "Add python.exe to PATH" before clicking Install — this step is easy to miss and is the single most common cause of "python is not recognized" errors afterward.
●	Follow the remaining prompts, then close and reopen any open Command Prompt/PowerShell windows.
●	Confirm with python --version or py --version.
On Linux (Ubuntu/Debian example):
sudo apt update
sudo apt install -y python3
Most Linux distributions ship with Python 3 preinstalled; the commands above are only needed if Step 1 reported it missing. (Package names and availability vary by distribution — consult your distribution's package manager documentation if apt isn't available.)
Confirm with python3 --version.
Step 3 — Save the file
Unlike the C# version, there is no project file or build configuration to set up — a single .py file is a complete, runnable Python program.
●	Create a new, empty folder anywhere convenient — for example, on macOS/Linux: mkdir ~/MathQuiz && cd ~/MathQuiz, or on Windows (Command Prompt): mkdir %USERPROFILE%\MathQuiz && cd %USERPROFILE%\MathQuiz.
●	Copy the downloaded math_quiz.py file directly into that folder.
You can copy it using Finder (macOS), File Explorer (Windows), or your file manager (Linux) — just drag-and-drop the file into the folder you created.
Step 4 — Run it
python3 math_quiz.py
(On Windows, if python3 isn't recognized, use python math_quiz.py or py math_quiz.py instead.)
There is no separate build/compile step the way dotnet build compiles the C# version ahead of time — Python is interpreted, so this single command reads, parses, and immediately begins executing the file. You should see:
=== Math Quiz ===
Covers arithmetic, algebra, geometry, trigonometry, calculus, linear algebra, and statistics.

Choose a topic:
  1) Arithmetic
  2) Algebra
  ...
Interact with it exactly like any command-line program: type your menu choice and press Enter, type each answer and press Enter.
Step 5 — (Optional) Make it double-clickable
Python scripts are typically run from a terminal, but a couple of lightweight options exist if you'd like to avoid typing the command each time:
●	macOS/Linux: run chmod +x math_quiz.py once, and add a shebang line (#!/usr/bin/env python3) as the very first line of the file; the script can then be run directly as ./math_quiz.py.
●	Windows: right-click math_quiz.py in File Explorer and choose "Open with" → Python — the standard installer already associates .py files with the Python launcher, so double-clicking runs it directly (though the console window will close immediately when the program ends unless launched from an existing terminal).
●	Any platform: package it into a single standalone executable with a tool such as PyInstaller (pip install pyinstaller, then pyinstaller --onefile math_quiz.py), which bundles the interpreter itself so the result can run on a machine without Python installed — the closest Python equivalent to the C# version's dotnet publish --self-contained step.
Troubleshooting common issues
Symptom	Likely cause	Fix
python3: command not found	Python isn't installed, or only the Microsoft Store stub is on PATH (Windows)	Install Python from python.org and confirm "Add python.exe to PATH" was checked during setup (Windows), then reopen the terminal
'python' works but 'python3' doesn't (or vice versa)	Some platforms alias the interpreter differently	Try the other command, or use 'py' on Windows; any of them is fine as long as 'python --version' reports 3.9+
SyntaxError pointing at an f-string or type hint	An old Python 2 interpreter is being invoked instead of Python 3	Run 'python3 --version' to confirm you're on Python 3.9 or later; reinstall if not
Program exits immediately without letting you type	input() received EOF because stdin isn't an interactive terminal (e.g. running through a script or piped input)	Run 'python3 math_quiz.py' directly in an interactive terminal window, not through a pipe or redirected input
ModuleNotFoundError for a project file	The terminal's current directory isn't the folder containing math_quiz.py	cd into the folder that contains math_quiz.py before running the command
Numbers with a comma decimal separator (e.g. '12,5') are always rejected	This is expected, not a bug	Type the invariant/US format ('12.5'); float() always expects a period as the decimal separator regardless of your system locale

11. Runtime Walkthrough: What Happens When You Run It
This section traces through an actual session line by line — everything that appears on screen, in order, paired with exactly which piece of code produced it and what's happening internally at that moment. The example below plays a 3-question Arithmetic round, then declines to play again — the identical scenario walked through in the original C# documentation, reproduced here to show that the observable behavior is unchanged.

11.1 Program startup
The moment python3 math_quiz.py is run, the Python interpreter executes the module top to bottom. Before main() is even called, module-level code runs in order: imports, the Question dataclass and every function definition are registered, and then, near the bottom of the file, the line categories = build_categories() executes — fully constructing the topic dictionary (Section 6) before the if __name__ == "__main__": guard is even reached. This happens once, ever, for the whole program's run, no matter how many rounds are played — functionally identical to how the C# version's static field initializer ran once before Main().

Only then does main() run, printing two fixed lines:
=== Math Quiz ===
Covers arithmetic, algebra, geometry, trigonometry, calculus, linear algebra, and statistics.
Nothing dynamic yet — no randomness, no state — this is pure static output from two print() calls at the very top of main(). Immediately after, play_again is initialized to True and the while play_again: loop begins its first iteration.

11.2 The topic menu
Choose a topic:
  1) Arithmetic
  2) Algebra
  3) Geometry
  4) Trigonometry
  5) Calculus
  6) Linear Algebra
  7) Statistics
  8) Mixed (all topics)
Enter a number: 
What's happening internally: this is ask_for_category() executing. The numbered list isn't hardcoded text — it's generated by iterating categories.keys() (Section 3.1), so the exact order shown here matches the insertion order used inside build_categories(). The "8) Mixed" line is appended separately, one past the last real topic. The prompt is printed with Python's input(), which — unlike a separate print followed by a read — both displays its prompt text and blocks for a line of input in one call, so the cursor sits right after "Enter a number: " waiting for you to type.
Suppose you type 1 and press Enter. try_parse_int("1") succeeds and returns 1, which is within the valid range [1, names count] where names count = 7, so the function returns names[0], which is "Arithmetic". Control returns to main().

11.3 The question-count prompt
How many questions? (default 10): 
Suppose you type 3 and press Enter. ask_for_question_count() parses it successfully and returns 3. Control returns to main(), which now calls run_quiz("Arithmetic", 3).

11.4 Inside the quiz loop — Question 1
The loop variable i starts at 0. With question_count = 3:
progress = 0 / (3 - 1)  # = 0.0
progress is exactly 0.0 for the very first question, every time, in every round — the earliest possible position in the difficulty curve.
generate_question("Arithmetic", 0.0) runs next:
●	pool is set to the Arithmetic list (10 generators long, indices 0–9).
●	target_index = round(0.0 * 9) = 0.
●	window_start = max(0, 0 - 1) = 0.
●	chosen_index = randomizer.randint(0, 0) — since the range only contains the single value 0, chosen_index is always 0.
●	pool[0]() is invoked — the lambda lambda: whole_addition(1, 20) — which internally calls randomizer.randint(1, 20) twice to pick two addends, say 7 and 12, and returns a Question with prompt = "7 + 12", answer = 19, tolerance = 0.001, time_limit_seconds = 12.
Back in run_quiz, this prints:
Question 1 of 3
[12s allowed] 7 + 12 = 
What's happening internally: the blank line comes from an unconditional print() at the top of the loop body (visual spacing between questions). Immediately after printing the prompt, time.perf_counter() begins timing, and the program blocks on input(), waiting for you to type.
Suppose you type 19 and press Enter after 3 seconds. Grading runs:
●	within_time: 3s <= 12s → True.
●	parsed: "19" parses cleanly to 19.0 → True.
●	is_correct: |19.0 - 19.0| = 0 <= 0.001 → True.
Correct!
correct_count increments to 1.
11.5 Question 2 — difficulty progresses
Now i = 1:
progress = 1 / (3 - 1)  # = 0.5
Inside generate_question:
●	target_index = round(0.5 * 9) = round(4.5). Note: Python's round() uses banker's rounding by default (rounds half-values to the nearest even integer), exactly like C#'s Math.Round — so 4.5 rounds to 4, not 5, in both versions.
●	window_start = max(0, 4 - 1) = 3.
●	chosen_index = randomizer.randint(3, 4) — randomly either 3 or 4.
●	Index 3 is lambda: whole_division(2, 10); index 4 is decimal_addition. Suppose the random draw picks index 3.
whole_division(2, 10) picks a divisor (say 4) and a quotient (say 9) independently, then computes dividend = 4 * 9 = 36, guaranteeing a clean result. It returns prompt = "36 / 4", answer = 9.
Question 2 of 3
[15s allowed] 36 / 4 = 
Suppose you type 9. It's correct — Correct! prints, correct_count becomes 2.
11.6 Question 3 — an incorrect answer
i = 2, progress = 2 / 2 = 1.0 — the maximum, guaranteeing the hardest available tier this round.
●	target_index = round(1.0 * 9) = 9 — the very last index in the Arithmetic list, percentage_change.
●	window_start = max(0, 9 - 1) = 8.
●	chosen_index is randomly 8 (decimal_multiplication) or 9 (percentage_change). Suppose it lands on 9.
percentage_change() picks a percent from {10, 20, 25, 50} (say 20), a base number (say 85), and randomly decides increase or decrease (say decrease). answer = round(85 * (1 - 0.20), 2) = 68.0.
Question 3 of 3
[24s allowed] 85 decreased by 20% = 
Suppose you type 70 (a mistake) and press Enter within time.
●	within_time: True.
●	parsed: True.
●	is_correct: |70 - 68| = 2, which is not <= tolerance (0.2) → False.
Since within_time is True but the answer itself is wrong, the else branch (not the not within_time branch) runs:
Not quite. The answer was 68.
Internally, format_answer(68.0) is called — since 68.0 == math.floor(68.0), it's formatted as "68" rather than "68.0". Exactly this string is appended to missed_summaries:
85 decreased by 20% = 68
(the "(ran out of time)" suffix only gets added on timeout misses, not wrong-answer misses — see Section 4.2).
11.7 End-of-round summary
The loop has now run all 3 iterations, so control falls out of it to the summary block:
You got 2 out of 3 correct.

Questions to review:
  85 decreased by 20% = 68
What's happening internally: correct_count (2) and question_count (3, the original parameter) are printed directly. Then, since missed_summaries has exactly one entry from Question 3, the review header and every stored summary line are printed via a for loop. If you'd gotten all three questions right, this entire block — header included — would be skipped, since the surrounding if missed_summaries: only fires when the list is non-empty (an empty list is falsy in Python, so this reads naturally without an explicit .Count > 0 check the way C# needed).
11.8 The play-again prompt and program exit
Control returns from run_quiz back into the while play_again: loop in main():
Play again? (y/n): 
Suppose you type n and press Enter.
play_again = response is not None and response.strip().lower().startswith("y")
"n".strip().lower() is "n", and "n".startswith("y") is False, so play_again becomes False. The while loop's condition now fails, so the loop exits entirely — no new topic menu, no new question count, nothing further is asked.
The very last line in main() runs:
Thanks for playing!
main() then returns, the if __name__ == "__main__": block finishes, and the Python process exits. The terminal returns you to your normal command prompt.

11.9 What a "Mixed" round looks like differently
If you'd chosen option 8) Mixed instead of a specific topic, the only difference happens inside generate_question (Section 5.2): before computing target_index, the function first rolls an independent random choice over all 7 topic names to decide which topic's list to scale into for that single question. This means in a Mixed round, you might see an Arithmetic question at low difficulty immediately followed by, say, a Calculus question also at low difficulty (since progress still governs how far into that topic's own list to scale) — the topic itself changes every question, but the "how hard within whichever topic got picked" logic is identical to a single-topic round. This behavior is unchanged from the C# version.

11.10 What happens on bad or empty input
A few edge cases worth knowing about, since they don't cause crashes but do affect scoring silently — all carried over unchanged from the original:
●	Typing something that isn't a number (e.g., "nineteen" instead of 19) — try_parse_float catches the ValueError that Python's float() raises and returns None, so parsed is False, which forces is_correct to False regardless of timing. This is treated exactly like a wrong answer: "Not quite. The answer was ..." is shown, and the question is added to the review list.
●	Just pressing Enter with no input — input() returns an empty string "", which also fails float() parsing, producing the same "wrong answer" outcome as above.
●	Taking longer than the time limit — even if you eventually type the mathematically correct number, within_time is checked before is_correct is allowed to be True (Section 4.2), so a correct-but-late answer is graded as a miss, specifically routed to the "Too slow!" message and the "(ran out of time)" summary suffix, rather than the generic "Not quite" message.
●	Pressing Ctrl+D (macOS/Linux) or Ctrl+Z then Enter (Windows) at an input() prompt — this sends end-of-file on stdin, which raises EOFError in Python rather than returning null the way C#'s Console.ReadLine() does at end of input. This is the one input-handling edge case where the direct translation diverges slightly: the C# version's response != null check exists specifically to handle that null-on-EOF case gracefully at the play-again prompt, whereas this Python port, run interactively as intended, will not normally encounter EOF unless stdin is redirected from an already-exhausted source (see the Troubleshooting table in Section 10 for that scenario).
