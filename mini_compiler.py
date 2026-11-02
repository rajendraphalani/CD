#!/usr/bin/env python3
"""
Mini Compiler for Educational Programming
-----------------------------------------
Phases : Lexical Analysis -> Syntax Analysis (AST) -> Semantic Analysis
         -> Intermediate Code (Three-Address Code) -> Execution
Usage  : python mini_compiler.py examples/sample1.mc
         python mini_compiler.py examples/sample1.mc --quiet     (output only)
         python mini_compiler.py --code "x = 5; PRINT x;"
         python mini_compiler.py --tests                          (run self tests)
"""
import sys
import argparse

# ============================================================ ERRORS
class CompilerError(Exception):
    def __init__(self, kind, line, msg):
        self.kind, self.line, self.msg = kind, line, msg
        super().__init__(f"{kind} Error | Line {line} — {msg}")


# ============================================================ 1. LEXER
KEYWORDS = {"INT", "IF", "ELSE", "WHILE", "PRINT"}
TWO_CHAR = {"==", "!=", "<=", ">="}
ONE_CHAR = {"+": "PLUS", "-": "MINUS", "*": "MUL", "/": "DIV", "<": "LT", ">": "GT",
            "=": "ASSIGN", ";": "SEMI", "(": "LPAREN", ")": "RPAREN",
            "{": "LBRACE", "}": "RBRACE"}
TWO_NAMES = {"==": "EQ", "!=": "NEQ", "<=": "LE", ">=": "GE"}


class Token:
    def __init__(self, type_, value, line):
        self.type, self.value, self.line = type_, value, line

    def __repr__(self):
        return f"({self.type}, {self.value!r}, line {self.line})"


def lex(src):
    tokens, i, line, n = [], 0, 1, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1; i += 1
        elif c in " \t\r":
            i += 1
        elif c == "#" or src.startswith("//", i):          # comments
            while i < n and src[i] != "\n":
                i += 1
        elif c.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            if j < n and (src[j].isalpha() or src[j] == "_"):
                raise CompilerError("Lexical", line, f"Invalid identifier '{src[i:j+1]}...' (cannot start with a digit)")
            tokens.append(Token("NUMBER", int(src[i:j]), line)); i = j
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            if word.upper() in KEYWORDS:
                tokens.append(Token(word.upper(), word.upper(), line))
            else:
                tokens.append(Token("ID", word, line))
            i = j
        elif src[i:i+2] in TWO_CHAR:
            tokens.append(Token(TWO_NAMES[src[i:i+2]], src[i:i+2], line)); i += 2
        elif c in ONE_CHAR:
            tokens.append(Token(ONE_CHAR[c], c, line)); i += 1
        else:
            raise CompilerError("Lexical", line, f"Unknown character '{c}'")
    tokens.append(Token("EOF", "EOF", line))
    return tokens


# ============================================================ 2. PARSER (AST)
# Grammar:
#  program   -> stmt*
#  stmt      -> INT ID ('=' expr)? ';' | ID '=' expr ';' | PRINT expr ';'
#             | IF '(' cond ')' block (ELSE block)? | WHILE '(' cond ')' block
#  block     -> '{' stmt* '}'
#  cond      -> expr (<|>|==|!=|<=|>=) expr
#  expr      -> term (('+'|'-') term)*      term -> factor (('*'|'/') factor)*
#  factor    -> NUMBER | ID | '(' expr ')' | '-' factor
class Node:
    def __init__(self, kind, line, **kw):
        self.kind, self.line = kind, line
        self.__dict__.update(kw)


class Parser:
    def __init__(self, tokens):
        self.t, self.p = tokens, 0

    @property
    def cur(self):
        return self.t[self.p]

    def eat(self, type_, what=None):
        if self.cur.type != type_:
            prev_line = self.t[self.p - 1].line if self.p else self.cur.line
            line = prev_line if self.cur.type in ("EOF", "RBRACE") or type_ == "SEMI" else self.cur.line
            found = "end of file" if self.cur.type == "EOF" else f"'{self.cur.value}'"
            raise CompilerError("Syntax", line, f"Expected {what or type_} but found {found}")
        tok = self.cur; self.p += 1
        return tok

    def program(self):
        stmts = []
        while self.cur.type != "EOF":
            stmts.append(self.stmt())
        return Node("Program", 1, body=stmts)

    def block(self):
        self.eat("LBRACE", "'{'")
        body = []
        while self.cur.type not in ("RBRACE", "EOF"):
            body.append(self.stmt())
        self.eat("RBRACE", "'}'")
        return body

    def stmt(self):
        c = self.cur
        if c.type == "INT":
            self.p += 1
            name = self.eat("ID", "variable name")
            init = None
            if self.cur.type == "ASSIGN":
                self.p += 1; init = self.expr()
            self.eat("SEMI", "';'")
            return Node("Decl", c.line, name=name.value, init=init)
        if c.type == "ID":
            self.p += 1
            self.eat("ASSIGN", "'='")
            e = self.expr()
            self.eat("SEMI", "';'")
            return Node("Assign", c.line, name=c.value, expr=e)
        if c.type == "PRINT":
            self.p += 1
            e = self.expr()
            self.eat("SEMI", "';'")
            return Node("Print", c.line, expr=e)
        if c.type == "IF":
            self.p += 1
            self.eat("LPAREN", "'('"); cond = self.cond(); self.eat("RPAREN", "')'")
            then = self.block(); els = None
            if self.cur.type == "ELSE":
                self.p += 1; els = self.block()
            return Node("If", c.line, cond=cond, then=then, els=els)
        if c.type == "WHILE":
            self.p += 1
            self.eat("LPAREN", "'('"); cond = self.cond(); self.eat("RPAREN", "')'")
            return Node("While", c.line, cond=cond, body=self.block())
        found = "end of file" if c.type == "EOF" else f"'{c.value}'"
        raise CompilerError("Syntax", c.line, f"Unexpected {found}; a statement was expected")

    def cond(self):
        left = self.expr()
        if self.cur.type not in ("LT", "GT", "EQ", "NEQ", "LE", "GE"):
            raise CompilerError("Syntax", self.cur.line, "Expected a relational operator (<, >, ==, !=, <=, >=)")
        op = self.cur; self.p += 1
        return Node("Cond", op.line, op=op.value, left=left, right=self.expr())

    def expr(self):
        node = self.term()
        while self.cur.type in ("PLUS", "MINUS"):
            op = self.cur; self.p += 1
            node = Node("BinOp", op.line, op=op.value, left=node, right=self.term())
        return node

    def term(self):
        node = self.factor()
        while self.cur.type in ("MUL", "DIV"):
            op = self.cur; self.p += 1
            node = Node("BinOp", op.line, op=op.value, left=node, right=self.factor())
        return node

    def factor(self):
        c = self.cur
        if c.type == "NUMBER":
            self.p += 1; return Node("Num", c.line, value=c.value)
        if c.type == "ID":
            self.p += 1; return Node("Var", c.line, name=c.value)
        if c.type == "LPAREN":
            self.p += 1; e = self.expr(); self.eat("RPAREN", "')'"); return e
        if c.type == "MINUS":
            self.p += 1
            return Node("BinOp", c.line, op="-", left=Node("Num", c.line, value=0), right=self.factor())
        found = "end of file" if c.type == "EOF" else f"'{c.value}'"
        raise CompilerError("Syntax", c.line, f"Expected a number, variable or '(' but found {found}")


def ast_lines(n, indent=0):
    pad = "  " * indent
    k = n.kind
    if k == "Program":
        out = [pad + "Program"]
        for s in n.body: out += ast_lines(s, indent + 1)
        return out
    if k == "Decl":
        out = [f"{pad}Declare {n.name}"]
        if n.init: out += ast_lines(n.init, indent + 1)
        return out
    if k == "Assign":
        return [f"{pad}Assign {n.name} ="] + ast_lines(n.expr, indent + 1)
    if k == "Print":
        return [pad + "Print"] + ast_lines(n.expr, indent + 1)
    if k == "If":
        out = [pad + "If"] + ast_lines(n.cond, indent + 1) + [pad + "  Then"]
        for s in n.then: out += ast_lines(s, indent + 2)
        if n.els:
            out.append(pad + "  Else")
            for s in n.els: out += ast_lines(s, indent + 2)
        return out
    if k == "While":
        out = [pad + "While"] + ast_lines(n.cond, indent + 1) + [pad + "  Do"]
        for s in n.body: out += ast_lines(s, indent + 2)
        return out
    if k in ("Cond", "BinOp"):
        return [f"{pad}{n.op}"] + ast_lines(n.left, indent + 1) + ast_lines(n.right, indent + 1)
    if k == "Num":
        return [f"{pad}{n.value}"]
    if k == "Var":
        return [f"{pad}{n.name}"]


# ============================================================ 3. SEMANTIC ANALYSIS
def semantic(prog):
    """Symbol table: name -> 'declared' (int). A variable becomes defined on first
    assignment (so 'x = 10;' works) but must be defined BEFORE it is read."""
    table, log = {}, []

    def check_expr(e):
        if e.kind == "Var":
            if e.name not in table:
                raise CompilerError("Semantic", e.line, f"Variable '{e.name}' is not declared")
            if not table[e.name]:
                raise CompilerError("Semantic", e.line, f"Variable '{e.name}' is used before it is given a value")
        elif e.kind in ("BinOp", "Cond"):
            check_expr(e.left); check_expr(e.right)
            if e.kind == "BinOp" and e.op == "/" and e.right.kind == "Num" and e.right.value == 0:
                raise CompilerError("Semantic", e.line, "Division by zero")

    def check(stmts):
        for s in stmts:
            if s.kind == "Decl":
                if s.name in table:
                    raise CompilerError("Semantic", s.line, f"Variable '{s.name}' is already declared")
                if s.init: check_expr(s.init)
                table[s.name] = s.init is not None
                log.append(f"Line {s.line}: declared '{s.name}' (int)" + (" with initial value" if s.init else ""))
            elif s.kind == "Assign":
                check_expr(s.expr)
                if s.name not in table:
                    log.append(f"Line {s.line}: '{s.name}' created by first assignment (int)")
                table[s.name] = True
            elif s.kind == "Print":
                check_expr(s.expr); log.append(f"Line {s.line}: PRINT expression is valid")
            elif s.kind == "If":
                check_expr(s.cond); check(s.then)
                if s.els: check(s.els)
                log.append(f"Line {s.line}: IF condition is valid")
            elif s.kind == "While":
                check_expr(s.cond); check(s.body)
                log.append(f"Line {s.line}: WHILE condition is valid")

    check(prog.body)
    return table, log


# ============================================================ 4. INTERMEDIATE CODE (TAC)
class TACGen:
    def __init__(self):
        self.code, self.tn, self.ln = [], 0, 0

    def temp(self):
        self.tn += 1; return f"t{self.tn}"

    def label(self):
        self.ln += 1; return f"L{self.ln}"

    def emit(self, *ins):
        self.code.append(ins)

    def expr(self, e):
        if e.kind == "Num": return str(e.value)
        if e.kind == "Var": return e.name
        a, b = self.expr(e.left), self.expr(e.right)
        t = self.temp(); self.emit("bin", t, a, e.op, b)
        return t

    def stmts(self, lst):
        for s in lst: self.stmt(s)

    def stmt(self, s):
        k = s.kind
        if k == "Decl":
            if s.init: self.emit("copy", s.name, self.expr(s.init))
        elif k == "Assign":
            self.emit("copy", s.name, self.expr(s.expr))
        elif k == "Print":
            self.emit("print", self.expr(s.expr))
        elif k == "If":
            a, b = self.expr(s.cond.left), self.expr(s.cond.right)
            t = self.temp(); self.emit("bin", t, a, s.cond.op, b)
            l_else, l_end = self.label(), self.label()
            self.emit("iffalse", t, l_else)
            self.stmts(s.then)
            if s.els:
                self.emit("goto", l_end); self.emit("label", l_else)
                self.stmts(s.els); self.emit("label", l_end)
            else:
                self.emit("label", l_else)
        elif k == "While":
            l_top, l_end = self.label(), self.label()
            self.emit("label", l_top)
            a, b = self.expr(s.cond.left), self.expr(s.cond.right)
            t = self.temp(); self.emit("bin", t, a, s.cond.op, b)
            self.emit("iffalse", t, l_end)
            self.stmts(s.body)
            self.emit("goto", l_top); self.emit("label", l_end)


def tac_text(ins):
    k = ins[0]
    if k == "bin":   return f"{ins[1]} = {ins[2]} {ins[3]} {ins[4]}"
    if k == "copy":  return f"{ins[1]} = {ins[2]}"
    if k == "print": return f"PRINT {ins[1]}"
    if k == "iffalse": return f"IF_FALSE {ins[1]} GOTO {ins[2]}"
    if k == "goto":  return f"GOTO {ins[1]}"
    if k == "label": return f"{ins[1]}:"


# ============================================================ 5. EXECUTION (TAC interpreter)
def run_tac(code, max_steps=100000):
    labels = {ins[1]: i for i, ins in enumerate(code) if ins[0] == "label"}
    env, out, pc, steps = {}, [], 0, 0

    def val(x):
        return int(x) if x.lstrip("-").isdigit() else env[x]

    while pc < len(code):
        steps += 1
        if steps > max_steps:
            raise CompilerError("Runtime", 0, "Program stopped: too many steps (possible infinite loop)")
        ins = code[pc]; k = ins[0]
        if k == "bin":
            a, op, b = val(ins[2]), ins[3], val(ins[4])
            if   op == "+": r = a + b
            elif op == "-": r = a - b
            elif op == "*": r = a * b
            elif op == "/":
                if b == 0: raise CompilerError("Runtime", 0, "Division by zero")
                r = int(a / b)
            else: r = int({"<": a < b, ">": a > b, "==": a == b, "!=": a != b, "<=": a <= b, ">=": a >= b}[op])
            env[ins[1]] = r
        elif k == "copy":    env[ins[1]] = val(ins[2])
        elif k == "print":   out.append(str(val(ins[1])))
        elif k == "iffalse":
            if val(ins[1]) == 0: pc = labels[ins[2]]
        elif k == "goto":    pc = labels[ins[1]]
        pc += 1
    return out, {k: v for k, v in env.items() if not k.startswith("t")}


# ============================================================ DRIVER
def banner(title):
    print("\n" + "=" * 60 + f"\n {title}\n" + "=" * 60)


def compile_and_run(src, verbose=True):
    if verbose:
        banner("SOURCE CODE")
        for i, l in enumerate(src.splitlines(), 1): print(f"{i:>3} | {l}")
    tokens = lex(src)
    if verbose:
        banner("PHASE 1: LEXICAL ANALYSIS (TOKENS)")
        for t in tokens[:-1]: print(f"  Line {t.line:<3} {t.type:<7} {t.value!r}")
        print(f"  -> {len(tokens)-1} tokens generated")
    prog = Parser(tokens).program()
    if verbose:
        banner("PHASE 2: SYNTAX ANALYSIS (ABSTRACT SYNTAX TREE)")
        print("\n".join(ast_lines(prog)))
    table, log = semantic(prog)
    if verbose:
        banner("PHASE 3: SEMANTIC ANALYSIS")
        for l in log: print("  " + l)
        print("  Symbol table:", ", ".join(f"{k}:int" for k in table))
        print("  -> No semantic errors")
    g = TACGen(); g.stmts(prog.body)
    if verbose:
        banner("PHASE 4: INTERMEDIATE CODE (THREE-ADDRESS CODE)")
        for ins in g.code: print("  " + tac_text(ins))
    out, env = run_tac(g.code)
    if verbose:
        banner("PHASE 5: EXECUTION OUTPUT")
    print("\n".join(out) if out else "(no output)")
    if verbose:
        print("\n  Final variables:", env)
    return out


def self_test():
    cases = [
        ("x = 10; y = 20; z = x + y; PRINT z;", ["30"], None),
        ("int i = 1; WHILE (i <= 3) { PRINT i * i; i = i + 1; }", ["1", "4", "9"], None),
        ("int a = 5; IF (a > 3) { PRINT 1; } ELSE { PRINT 0; }", ["1"], None),
        ("PRINT 2 + 3 * 4;", ["14"], None),
        ("x = 1;\ny = 2;\nz = 3;\nPRINT a;", None, "Semantic"),
        ("x = 5 $ 3;", None, "Lexical"),
        ("x = 5\nPRINT x;", None, "Syntax"),
        ("int x = 4; PRINT x / 0;", None, "Semantic"),
    ]
    ok = 0
    for src, expected, err in cases:
        try:
            out = compile_and_run(src, verbose=False) if expected is not None else None
            if expected is None:
                compile_and_run(src, verbose=False)
                status = "FAIL (no error raised)"
            else:
                status = "PASS" if out == expected else f"FAIL got {out}"
        except CompilerError as e:
            status = "PASS" if e.kind == err else f"FAIL wrong error {e}"
            if status == "PASS": print(f"    (caught) {e}")
        print(("  " if status == "PASS" else "! ") + f"{status:<6} {src!r}")
        ok += status == "PASS"
    print(f"\n{ok}/{len(cases)} tests passed")
    return ok == len(cases)


def main():
    ap = argparse.ArgumentParser(description="Mini Compiler for Educational Programming")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--code", help="compile a code string directly")
    ap.add_argument("--quiet", action="store_true", help="show only program output")
    ap.add_argument("--tests", action="store_true", help="run built-in tests")
    a = ap.parse_args()
    if a.tests:
        sys.exit(0 if self_test() else 1)
    if a.code: src = a.code.replace("\\n", "\n")
    elif a.file: src = open(a.file).read()
    else: ap.error("give a source file, --code, or --tests")
    try:
        compile_and_run(src, verbose=not a.quiet)
    except CompilerError as e:
        banner("COMPILATION FAILED")
        print(f"  {e.kind} Error | Line {e.line} — {e.msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
