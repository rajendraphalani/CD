# Mini Compiler for Educational Programming

**Team 11** — 2420030609 Rajendra · 2420030615 Mallikarjun · 2420030370 Praveen
**Guide:** Dr. Sri Niraja

## Abstract

Compiler design concepts such as tokenization, parsing, symbol tables and intermediate code are difficult for students to grasp when they are taught only as theory. This project presents a *Mini Compiler for Educational Programming*, a small compiler for a simple teaching language, implemented in Python, that makes every stage of compilation visible.

The language supports integer variables, assignment, arithmetic operators (+, -, *, /), relational operators (<, >, ==, !=, <=, >=), IF / ELSE statements, WHILE loops and a PRINT statement. A source program passes through five phases: the **lexical analyzer** converts characters into tokens; a **recursive-descent parser** checks the grammar and builds an Abstract Syntax Tree (AST); the **semantic analyzer** maintains a symbol table and checks declarations and valid operations; the **intermediate code generator** produces three-address code (TAC) with temporaries and labels; and an **interpreter** executes the TAC to produce the program output.

A central feature is the **educational display**: the tool prints the source code, token list, AST, semantic results, intermediate code and final output one phase after another. A dedicated error handler reports lexical, syntax, semantic and runtime errors with line numbers, for example *"Line 4 — Variable 'a' is not declared"*, so students see exactly where and why compilation fails. The compiler was tested on valid programs (sequential code, loops, conditionals, operator precedence) and on invalid programs, and passed all 8 built-in test cases.

The project connects compiler theory with a working implementation in a small, understandable language. Future work includes AST visualization, syntax highlighting, more data types, basic optimization and real virtual-machine or assembly code generation.

**Keywords:** Compiler Design, Lexical Analysis, Parsing, AST, Semantic Analysis, Three-Address Code, Educational Tool
