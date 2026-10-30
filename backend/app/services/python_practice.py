"""A bounded interpreter for Orbit's introductory Python practice challenges.

It deliberately does not call eval/exec or expose files, imports, processes, or network APIs.
This is a small teaching language, not a general Python sandbox.
"""

import ast
import operator
from dataclasses import dataclass, field


class PracticeError(ValueError):
    pass


BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod}
CMPOPS = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}
MAX_VALUE_SIZE = 12000


def bounded_binop(op, left, right):
    if isinstance(op, ast.Add) and isinstance(left, str) and isinstance(right, str) and len(left) + len(right) > MAX_VALUE_SIZE:
        raise PracticeError("Text values are limited to 12,000 characters.")
    if isinstance(op, ast.Mult):
        if isinstance(left, str) and isinstance(right, int) and len(left) * max(right, 0) > MAX_VALUE_SIZE:
            raise PracticeError("Text values are limited to 12,000 characters.")
        if isinstance(right, str) and isinstance(left, int) and len(right) * max(left, 0) > MAX_VALUE_SIZE:
            raise PracticeError("Text values are limited to 12,000 characters.")
    result = BINOPS[type(op)](left, right)
    if isinstance(result, int) and result.bit_length() > 256:
        raise PracticeError("Numbers are too large for this practice space.")
    return result


@dataclass
class Interpreter:
    env: dict[str, object] = field(default_factory=dict)
    output: list[str] = field(default_factory=list)
    steps: int = 0
    max_steps: int = 3000
    max_output: int = 12000

    def tick(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise PracticeError("This example used too many steps. Try a shorter loop.")

    def expr(self, node: ast.expr):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise PracticeError(f"'{node.id}' has not been defined yet.")
            return self.env[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in BINOPS:
            return bounded_binop(node.op, self.expr(node.left), self.expr(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Not)):
            value = self.expr(node.operand)
            return -value if isinstance(node.op, ast.USub) else (+value if isinstance(node.op, ast.UAdd) else not value)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in CMPOPS:
            return CMPOPS[type(node.ops[0])](self.expr(node.left), self.expr(node.comparators[0]))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"range", "str", "int", "float"}:
            args = [self.expr(arg) for arg in node.args]
            if node.func.id == "range":
                result = range(*args)
                if len(result) > 1000:
                    raise PracticeError("range() is limited to 1,000 steps in this practice space.")
                return result
            return {"str": str, "int": int, "float": float}[node.func.id](*args)
        if isinstance(node, ast.JoinedStr):
            return "".join(str(self.expr(part.value)) if isinstance(part, ast.FormattedValue) else str(part.value) for part in node.values)
        if isinstance(node, ast.FormattedValue):
            return self.expr(node.value)
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self.expr(item) for item in node.elts]
        if isinstance(node, ast.Subscript):
            return self.expr(node.value)[self.expr(node.slice)]
        if isinstance(node, ast.ListComp):
            if len(node.generators) != 1 or not isinstance(node.generators[0].target, ast.Name):
                raise PracticeError("Only simple list comprehensions are supported.")
            gen = node.generators[0]
            items = self.expr(gen.iter)
            if len(items) > 1000:
                raise PracticeError("List comprehensions are limited to 1,000 items.")
            previous = self.env.get(gen.target.id)
            had_previous = gen.target.id in self.env
            result = []
            for item in items:
                self.tick()
                self.env[gen.target.id] = item
                if all(self.expr(test) for test in gen.ifs):
                    result.append(self.expr(node.elt))
            if had_previous:
                self.env[gen.target.id] = previous
            else:
                self.env.pop(gen.target.id, None)
            return result
        raise PracticeError(f"This practice space does not support {type(node).__name__} yet.")

    def statement(self, node: ast.stmt) -> None:
        self.tick()
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            self.env[node.targets[0].id] = self.expr(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            self.env[node.target.id] = self.expr(node.value) if node.value else None
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
            line = " ".join(str(self.expr(arg)) for arg in node.value.args)
            self.output.append(line)
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            values = self.expr(node.iter)
            if len(values) > 1000:
                raise PracticeError("Loops are limited to 1,000 steps.")
            for value in values:
                self.env[node.target.id] = value
                for statement in node.body:
                    self.statement(statement)
        elif isinstance(node, ast.If):
            body = node.body if self.expr(node.test) else node.orelse
            for statement in body:
                self.statement(statement)
        else:
            raise PracticeError(f"This practice space does not support {type(node).__name__} yet.")
        if sum(len(line) + 1 for line in self.output) > self.max_output:
            raise PracticeError("Output is too long. Try a smaller example.")


def run_practice(source: str) -> str:
    if len(source) > 8000:
        raise PracticeError("Keep examples under 8,000 characters.")
    try:
        tree = ast.parse(source, mode="exec")
        interpreter = Interpreter()
        for statement in tree.body:
            interpreter.statement(statement)
        return "\n".join(interpreter.output)
    except (SyntaxError, ZeroDivisionError, TypeError, ValueError, IndexError, KeyError, RecursionError) as exc:
        if isinstance(exc, PracticeError):
            raise
        if isinstance(exc, SyntaxError):
            raise PracticeError(f"Python syntax: {exc.msg}") from exc
        raise PracticeError(str(exc)[:300]) from exc
