# Contributing to LLEO Framework

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/LLEO-Framework.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the environment: `source venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Install test dependencies: `pip install -r tests/requirements-test.txt`

## Development Process

### Setting Up Development Environment
1. Install required tools:
```bash
# Install development tools
pip install black mypy pytest pytest-cov
```

2. Configure pre-commit hooks:
```bash
pre-commit install
```

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document all public methods
- Keep functions focused and small
- Use meaningful variable names

### Testing
1. Run tests:
```bash
python run_tests.py --coverage
```

2. Run specific test categories:
```bash
python run_tests.py --unit-only
python run_tests.py --integration-only
```

### Documentation
- Update API documentation for new features
- Add docstrings to all public methods
- Include usage examples
- Update implementation guides

## Pull Request Process

1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

2. Make Changes
- Write code
- Add tests
- Update documentation

3. Run Quality Checks
```bash
# Run formatters
black .

# Run type checker
mypy .

# Run tests
python run_tests.py --coverage
```

4. Commit Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

5. Submit Pull Request
- Create PR against main branch
- Fill out PR template
- Request review

## Code Review Guidelines

### Reviewer Responsibilities
- Check code quality
- Verify test coverage
- Review documentation
- Test functionality

### Author Responsibilities
- Respond to feedback
- Update code as needed
- Maintain PR up-to-date

## Release Process

1. Version Update
- Update version in setup.py
- Update CHANGELOG.md
- Update documentation

2. Testing
- Run full test suite
- Verify documentation
- Check dependencies

3. Release
- Create release branch
- Tag release
- Update main branch

## Bug Reports

### Required Information
- Framework version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior

### Security Issues
- Report security issues privately
- Use security issue template
- Include impact assessment

## Feature Requests

### Proposal Process
1. Check existing issues/PRs
2. Create feature request issue
3. Discuss implementation
4. Submit proposal

### Required Information
- Use case
- Proposed solution
- Alternative approaches
- Implementation plan

## Community Guidelines

### Communication
- Be respectful
- Stay on topic
- Help others learn
- Share knowledge

### Support
- Use issue templates
- Search existing issues
- Provide relevant information
- Follow up on issues

## Development Workflow

### Branch Strategy
- main: stable releases
- develop: integration branch
- feature/*: new features
- fix/*: bug fixes
- release/*: release preparation

### Commit Messages
Follow conventional commits:
- feat: new feature
- fix: bug fix
- docs: documentation
- test: test addition/modification
- refactor: code refactoring
- style: formatting changes
- chore: maintenance tasks

### Code Organization
- Keep modules focused
- Follow project structure
- Use consistent naming
- Maintain separation of concerns

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.