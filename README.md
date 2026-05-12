# Fortran 77 Compiler (ANSI X3.9-1978)

This project consists of the development of a compiler for the **Fortran 77** programming language, built as part of the **Language Processing (2026)** course. The compiler translates Fortran 77 source code into machine code for the **EWVM** (Virtual Machine) provided by the university.

The compiler is implemented in **Python** using the **PLY** (Python Lex-Yacc) library and covers all mandatory stages of a compiler pipeline, as well as an optional optimization phase.

---

## 🏗 Project Structure

```text
PL_G16_2526/
├── Report.latex         # Technical report in LaTeX
├── src/                 # Compiler source code
│   ├── main.py          # Main compiler program (ponto de entrada)
│   ├── lexer.py         # Lexical analyzer (ply.lex)
│   ├── parser.py        # Syntax analyzer (ply.yacc)
│   ├── semantic.py      # Semantic analyzer
│   ├── codegen.py       # EWVM code generator
│   └── utils/           # Auxiliary modules and support
│       ├── errors.py    # Centralized error messaging system
│       └── colors.py    # Terminal styling definitions
├── tests/               # Test programs (.f and .vm)
└── README.md            # Project instructions
```


---

## ⚙️ Compiler Pipeline

The compiler processes Fortran 77 source code through the following stages:

1. **Lexical Analysis** — Tokenizes the source code using `ply.lex`. Supports free-form Fortran syntax with `!` comments. Handles the distinction between integer literals and line labels.

2. **Syntax Analysis** — Builds an Abstract Syntax Tree (AST) using `ply.yacc`. Enforces the strict declaration-before-execution structure of Fortran 77. Resolves operator precedence and handles the ambiguity between array access and function calls.

3. **Semantic Analysis** — Traverses the AST validating type compatibility, variable declarations, array bounds, label consistency, and subprogram signatures. Collects errors without stopping, maximizing feedback per compilation run.

4. **Optimization** — Produces an optimized AST through:
   - **Dead code elimination** after unconditional `GOTO`s and in static `IF` branches
   - **Removal of unused declarations** (variables, functions, subroutines)
   - **Constant folding** for compile-time evaluable expressions

5. **Code Generation** — Translates the optimized AST into EWVM instructions, handling arithmetic, control flow, arrays, I/O, and subprogram calls.

---

## 🚀 Supported Features

| Feature | Supported |
|:--------|:---------:|
| Integer, Real, Logical types | ✅ |
| Arithmetic, relational and logical expressions | ✅ |
| `IF-THEN-ELSE` / `ENDIF` | ✅ |
| `DO` loops with labels | ✅ |
| `GOTO` and label statements | ✅ |
| `READ` and `PRINT` | ✅ |
| 1D static arrays | ✅ |
| `FUNCTION` subprograms | ✅ |
| `SUBROUTINE` subprograms | ✅ |
| Intrinsic functions (`MOD`, `ABS`, `SQRT`, etc.) | ✅ |
| Optimization phase | ✅ |

---

## 🛠 How to Run

### Requirements

- Python 3.8+
- PLY library

Install PLY with:

```bash
pip install ply
```

### Compiling a Fortran file

```bash
python3 src/main.py  [options]
```

**Options:**

| Flag | Description |
|:-----|:------------|
| `-o, --output <file>` | Output file for VM code (default: `<input_file>.vm`) |
| `--no-opt` | Disable all optimizations |
| `--no-warn` | Suppress all warnings |
| `-h, --help` | Show help message |

**Examples:**

```bash
# Basic compilation
python3 src/main.py tests/factorial.f

# Custom output file
python3 src/main.py tests/factorial.f -o output/factorial.vm

# Compile without optimizations
python3 src/main.py tests/factorial.f --no-opt

# Suppress warnings
python3 src/main.py tests/factorial.f --no-warn
```

---

## 👥 Group Members

| Name | Student ID |
|:-----|:----------:|
| David Lopes Machado | a107325 |
| Rodrigo de Sousa Campos Pacheco da Rocha | a107335 |
| João Pedro Araújo Fernandes | a103568 |

---

## 📄 License

This project was developed for academic purposes at the **University of Minho**, 2026.

