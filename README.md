
# pyfix.py - Python Auto-Correction and Error Solver

## Project Overview

PyFix is a Python-based error detection and correction tool designed to help identify common errors in Python programs and provide corrected code.

The project analyzes Python source code, detects problems, attempts to correct supported errors, and displays the corrected code and execution output.

## Objectives

- Detect errors in Python source code.
- Identify the possible cause of an error.
- Automatically correct supported errors.
- Display the corrected Python code.
- Execute the corrected code and display the output.
- Make debugging easier for beginners and students.
- Provide a simple command-line interface.

## Features

- Python code error detection.
- Automatic correction for supported errors.
- Syntax and indentation error handling.
- Detection of common programming mistakes.
- Corrected code generation.
- Execution of corrected Python programs.
- Clear error and output messages.
- Command-line execution.
- Easy-to-use interface.

## Technologies Used

- Python 3
- Python Standard Library
- Abstract Syntax Tree (AST)
- Regular Expressions
- Subprocess
- Command-Line Interface

## Project Structure

PyFix-python-auto-correction/
│
├── PyFix.py
├── README.md
├── requirements.txt
└── .gitignore

## Requirements

- Python 3.8 or higher
- A computer with Python installed
- Command Prompt / Terminal / VS Code

## Installation

Clone the repository using:

git clone https://github.com/YOUR-USERNAME/PyFix-python-auto-correction.git

Move into the project directory:

cd PyFix-python-auto-correction

Install the required dependencies:

pip install -r requirements.txt

## How to Run

Run the main Python file using:

python PyFix.py

The program will start in the command line and allow the user to provide Python code for analysis.

## Working Process

1. The user provides Python source code.
2. PyFix analyzes the source code.
3. The program detects errors or possible problems.
4. PyFix attempts to correct supported errors.
5. The corrected code is displayed.
6. The corrected program is executed.
7. The execution result or remaining error is displayed to the user.

## Example

Input:

print("Hello World"

PyFix detects the syntax problem and attempts to generate a corrected version.

Corrected Code:

print("Hello World")

Output:

Hello World

## Purpose

PyFix is developed as an educational project to demonstrate Python programming, error handling, code analysis, debugging techniques, and automated code correction.

## Limitations

Automatic correction depends on the type and complexity of the error. Some highly complex logical, runtime, dependency-related, or environment-specific errors may require manual debugging.

## Future Enhancements

- Support for more Python error types.
- Improved code analysis.
- More advanced automatic debugging.
- AI-assisted error explanations.
- Support for multiple programming languages.
- Graphical user interface.
- Integrated code editor.
- More detailed error reports.

## Author

Pranav

## Project Type

VIT Flipped Course Project

## License

This project is created for educational
