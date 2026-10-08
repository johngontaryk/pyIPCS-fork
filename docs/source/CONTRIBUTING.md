# Contributing to pyIPCS

Thank you for your interest in contributing to pyIPCS! This guide will help you get started.

## Quick Links

- [Code of Conduct](https://github.com/openmainframeproject/tsc/blob/master/process/contribution_guidelines.md)
- [Developer Certificate of Origin (DCO)](https://github.com/openmainframeproject/tsc/blob/master/process/contribution_guidelines.md#developer-certificate-of-origin)

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/pyIPCS.git
cd pyIPCS
```

### 2. Set Up Development Environment

```bash
# Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

```bash
# Install development dependencies and pre-commit hooks
pip install -r requirements-dev.txt
pre-commit install
pre-commit install --hook-type commit-msg
```

### 3. Configure Git & DCO (Developer Certificate of Origin)

All contributions require a DCO sign-off. Configure your Git identity:

```bash
# Set your name and email for DCO sign-off
git config user.name "<YOUR_NAME>"
git config user.email "<YOUR_EMAIL>"
```

## Development Workflow

### 1. Create a Branch

```bash
# Fetch latest changes
git fetch upstream

# Create a new branch from develop
git checkout -b feature/your-feature-name upstream/develop
```

### 2. Make Your Changes

- Write your code
- Add tests for new functionality
- Update documentation as needed
- Follow the style guidelines (see below)

### 3. Test Your Changes

### 4. Commit Your Changes

**Important:** All commits must include a DCO signoff.

```bash
# Stage your changes
git add .

# Commit with DCO signoff (-s flag)
git commit -s -m "Add feature: description of your changes"
```

The `-s` flag adds a "Signed-off-by" line to your commit message:
```
Add feature: description of your changes

Signed-off-by: Your Name <your.email@example.com>
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name
```

Then create a pull request on GitHub from your branch to the `develop` branch of the main repository.

## Style Guidelines

### Python Code Style

#### Required Score

- **All code in `src/` must have a pylint score of 10.0**

```bash
# Check your code
pylint ./src
```

#### Code Formatting

We recommend using Black for consistent formatting:

```bash
# Install Black
pip install black

# Format your code
black ./src
```

#### Docstrings

- **All classes, functions, and methods must have docstrings**
- **Use Google-style docstrings**

### Documentation Style

#### Markdown

- Use markdownlint for consistency
- Follow the existing documentation structure
- Include code examples where appropriate

#### Spell Checking

- Use Code Spell Checker
- Add technical terms to `.cspell.json` if needed

### Required Tools

Install these VS Code extensions:

1. **markdownlint**
   - Identifier: `DavidAnson.vscode-markdownlint`

2. **Code Spell Checker**
   - Identifier: `streetsidesoftware.code-spell-checker`
