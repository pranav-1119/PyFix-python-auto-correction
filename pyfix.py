from flask import Flask, request, jsonify, render_template_string
import ast
import subprocess
import sys
import tempfile
import os
import difflib
import re

app = Flask(__name__)

ERROR_DATABASE = {
    "SyntaxError": "Python found invalid syntax in your program.",
    "IndentationError": "The indentation of one or more lines is incorrect.",
    "TabError": "Tabs and spaces are being mixed in indentation.",
    "NameError": "A variable or function name is being used before it is defined.",
    "TypeError": "An operation is being performed on incompatible data types.",
    "ZeroDivisionError": "A number is being divided by zero.",
    "ValueError": "A function received an inappropriate value or format.",
    "IndexError": "The program tried to access an index that does not exist.",
    "KeyError": "A dictionary key that does not exist was requested.",
}

def normalize_code(code):
    code = code.replace("\r\n", "\n").replace("\t", "    ")
    return "\n".join(line.rstrip() for line in code.splitlines())

def fix_common_typos(code):
    replacements = {
        "pritn(": "print(",
        "Print(": "print(",
        "leng(": "len(",
        "impoort ": "import ",
        "retrun ": "return ",
        "retrun(": "return(",
        "flase": "False",
        "ture": "True",
        "Nonee": "None",
    }
    for wrong, correct in replacements.items():
        code = code.replace(wrong, correct)
    return code

def fix_missing_colons(code):
    lines = code.splitlines()
    keywords = (
        "if ", "elif ", "else", "for ", "while ", "try",
        "except", "finally", "def ", "class ", "with ",
        "match ", "case "
    )
    fixed = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.endswith(":"):
            fixed.append(line)
            continue

        needs_colon = any(stripped.startswith(k) for k in keywords)
        if re.match(r"^def\s+\w+\s*\(.*\)\s*$", stripped):
            needs_colon = True
        if re.match(r"^class\s+\w+.*$", stripped):
            needs_colon = True

        fixed.append(line.rstrip() + ":" if needs_colon else line)
    return "\n".join(fixed)

def fix_indentation(code):
    lines = code.splitlines()
    fixed = []
    indent_level = 0
    dedent_keywords = ("elif ", "else:", "except", "finally:", "case ")
    previous_opens_block = False

    for raw_line in lines:
        stripped = raw_line.strip()

        if not stripped:
            fixed.append("")
            continue

        if stripped.startswith("#"):
            fixed.append("    " * indent_level + stripped)
            continue

        if any(stripped.startswith(k) for k in dedent_keywords):
            indent_level = max(0, indent_level - 1)

        if previous_opens_block:
            indent_level += 1
            previous_opens_block = False

        fixed.append("    " * indent_level + stripped)

        if stripped.endswith(":"):
            previous_opens_block = True

    return "\n".join(fixed)

def fix_brackets(code):
    pairs = {"(": ")", "[": "]", "{": "}"}
    closing = {")", "]", "}"}
    stack = []
    result = []
    quote = None
    escaped = False

    for char in code:
        result.append(char)

        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if quote is not None:
            continue

        if char in pairs:
            stack.append(pairs[char])
        elif char in closing and stack and stack[-1] == char:
            stack.pop()

    while stack:
        result.append(stack.pop())

    return "".join(result)

def auto_fix_code(code):
    original = code
    code = normalize_code(code)
    code = fix_common_typos(code)
    code = fix_missing_colons(code)
    code = fix_indentation(code)
    code = fix_brackets(code)
    code = re.sub(r"\n{4,}", "\n\n", code)
    return code, code != original

def analyze_syntax(code):
    try:
        ast.parse(code)
        return {
            "valid": True,
            "error_type": None,
            "message": "No syntax errors detected.",
            "line": None
        }
    except SyntaxError as e:
        return {
            "valid": False,
            "error_type": type(e).__name__,
            "message": str(e),
            "line": e.lineno
        }
    except Exception as e:
        return {
            "valid": False,
            "error_type": type(e).__name__,
            "message": str(e),
            "line": None
        }

def explain_error(error_type):
    return ERROR_DATABASE.get(
        error_type,
        "PyFix detected an error that needs further investigation."
    )

def suggest_name_error(code, error_message):
    match = re.search(r"name '([^']+)' is not defined", error_message)
    if not match:
        return None

    wrong_name = match.group(1)
    candidates = set()

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                candidates.add(node.id)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                candidates.add(node.name)
    except Exception:
        return None

    matches = difflib.get_close_matches(
        wrong_name, list(candidates), n=1, cutoff=0.5
    )
    return matches[0] if matches else None

def execute_code(code):
    filename = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            filename = f.name

        process = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            timeout=5,
            shell=False
        )

        return {
            "success": process.returncode == 0,
            "output": process.stdout,
            "error": process.stderr
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Execution stopped: program exceeded the 5-second limit."
        }
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except OSError:
                pass

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    code = data.get("code", "")

    if not code.strip():
        return jsonify({"success": False, "message": "Please enter Python code."})

    analysis = analyze_syntax(code)
    suggestion = None
    explanation = ""

    if not analysis["valid"]:
        explanation = explain_error(analysis["error_type"])
        suggestion = suggest_name_error(code, analysis["message"])

    fixed_code, changed = auto_fix_code(code)
    fixed_analysis = analyze_syntax(fixed_code)

    return jsonify({
        "success": True,
        "original_valid": analysis["valid"],
        "error_type": analysis["error_type"],
        "error_message": analysis["message"],
        "error_line": analysis["line"],
        "explanation": explanation,
        "suggestion": suggestion,
        "fixed_code": fixed_code,
        "fixed_code_valid": fixed_analysis["valid"],
        "changed": changed
    })

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json()
    code = data.get("code", "")

    if not code.strip():
        return jsonify({"success": False, "error": "No code entered."})

    syntax = analyze_syntax(code)
    if not syntax["valid"]:
        return jsonify({
            "success": False,
            "error": syntax["message"],
            "error_type": syntax["error_type"],
            "line": syntax["line"]
        })

    return jsonify(execute_code(code))

HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PyFix - Python Auto Fixer</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #090d18, #10182d, #071a20);
    color: white;
    min-height: 100vh;
}
.header {
    padding: 25px;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,.1);
}
.logo { font-size: 36px; font-weight: bold; letter-spacing: 2px; }
.logo span { color: #00e5ff; }
.subtitle { color: #aeb8cc; margin-top: 8px; }
.container { width: 92%; max-width: 1300px; margin: 25px auto; }
.editor-card, .panel {
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 18px;
    padding: 20px;
}
textarea {
    width: 100%;
    min-height: 400px;
    resize: vertical;
    background: #050811;
    color: #e7f6ff;
    border: 1px solid #26354f;
    border-radius: 12px;
    padding: 18px;
    font-family: Consolas, monospace;
    font-size: 15px;
    line-height: 1.6;
    outline: none;
}
textarea:focus { border-color: #00e5ff; }
.buttons { display: flex; gap: 12px; margin-top: 15px; flex-wrap: wrap; }
button {
    border: none; border-radius: 10px; padding: 13px 22px;
    font-size: 15px; font-weight: bold; cursor: pointer;
}
button:hover { transform: translateY(-2px); }
.analyze { background: #00bcd4; color: white; }
.fix { background: #673ab7; color: white; }
.run { background: #19a974; color: white; }
.clear { background: #374151; color: white; }
.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 20px;
}
.panel { min-height: 180px; }
.panel h2 { margin-top: 0; font-size: 19px; }
.status {
    padding: 12px;
    border-radius: 10px;
    background: #111827;
    margin-bottom: 10px;
}
.success { border-left: 4px solid #22c55e; }
.error { border-left: 4px solid #ef4444; }
.warning { border-left: 4px solid #f59e0b; }
pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    background: #050811;
    padding: 15px;
    border-radius: 10px;
    color: #dbeafe;
    overflow-x: auto;
}
.label {
    color: #8fa3bf;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
@media(max-width:800px) {
    .grid { grid-template-columns: 1fr; }
    textarea { min-height: 320px; }
}
</style>
</head>
<body>
<div class="header">
    <div class="logo">Py<span>Fix</span></div>
    <div class="subtitle">Python Error Detection & Automatic Code Correction System</div>
</div>

<div class="container">
<div class="editor-card">
<div class="label">Python Code</div><br>
<textarea id="code" spellcheck="false">for i in range(5)
print(i)</textarea>

<div class="buttons">
<button class="analyze" onclick="analyzeCode()">🔍 Analyze</button>
<button class="fix" onclick="fixCode()">🔧 Auto Fix</button>
<button class="run" onclick="runCode()">▶ Run</button>
<button class="clear" onclick="clearCode()">🗑 Clear</button>
</div>
</div>

<div class="grid">
<div class="panel">
<h2>🔎 Error Analysis</h2>
<div id="analysis">Enter code and click <strong>Analyze</strong>.</div>
</div>

<div class="panel">
<h2>🔧 Corrected Code</h2>
<pre id="fixedCode">Your corrected code will appear here.</pre>
</div>

<div class="panel">
<h2>📖 Explanation</h2>
<div id="explanation">PyFix will explain the detected problem here.</div>
</div>

<div class="panel">
<h2>▶ Program Output</h2>
<pre id="output">Program output will appear here.</pre>
</div>
</div>
</div>

<script>
async function analyzeCode() {
    const code = document.getElementById("code").value;
    const response = await fetch("/analyze", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({code: code})
    });
    const data = await response.json();

    if (!data.success) {
        document.getElementById("analysis").innerHTML =
            `<div class="status error">${data.message}</div>`;
        return;
    }

    let html = "";

    if (data.original_valid) {
        html = `<div class="status success">✅ No syntax errors detected.</div>`;
    } else {
        html = `<div class="status error">
            ❌ <strong>${data.error_type}</strong><br>
            ${data.error_message}
        </div>`;

        if (data.error_line) {
            html += `<div class="status warning">
                📍 Error near line ${data.error_line}
            </div>`;
        }

        if (data.suggestion) {
            html += `<div class="status warning">
                💡 Did you mean: <strong>${data.suggestion}</strong>?
            </div>`;
        }
    }

    document.getElementById("analysis").innerHTML = html;
    document.getElementById("fixedCode").textContent = data.fixed_code;
    document.getElementById("explanation").innerHTML =
        data.explanation || "Your code looks syntactically correct.";
}

async function fixCode() {
    await analyzeCode();

    const fixed = document.getElementById("fixedCode").textContent;

    if (fixed && fixed !== "Your corrected code will appear here.") {
        document.getElementById("code").value = fixed;
        document.getElementById("analysis").innerHTML +=
            `<div class="status success">✅ Auto-correction applied.</div>`;
    }
}

async function runCode() {
    const code = document.getElementById("code").value;
    document.getElementById("output").textContent = "Running...";

    const response = await fetch("/run", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({code: code})
    });

    const data = await response.json();

    if (data.success) {
        document.getElementById("output").textContent =
            data.output || "Program finished successfully.";
    } else {
        document.getElementById("output").textContent =
            "❌ " + (data.error || "Unknown error");
    }
}

function clearCode() {
    document.getElementById("code").value = "";
    document.getElementById("fixedCode").textContent =
        "Your corrected code will appear here.";
    document.getElementById("analysis").innerHTML =
        "Enter Python code and click Analyze.";
    document.getElementById("explanation").innerHTML =
        "PyFix will explain the detected problem here.";
    document.getElementById("output").textContent =
        "Program output will appear here.";
}
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

if __name__ == "__main__":
    print("=" * 60)
    print("             PYFIX - PYTHON AUTO FIXER")
    print("=" * 60)
    print("Server: http://127.0.0.1:5000")
    print("Press CTRL+C to stop.")
    app.run(host="127.0.0.1", port=5000, debug=True)
