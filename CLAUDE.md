# Claude Development Guidelines

This file contains project-specific guidelines for Claude Code when working on the crittercam project.

## Code Style

### Comments
- Use docstrings for all functions, classes, and modules
- Follow Google-style docstrings
- Add inline comments for complex logic
- Avoid obvious comments
- Comments should start with lowercase letters

### Type Hints
- Use type hints for all function parameters and return values
- Import types from typing module when needed
- Use Union, Optional, List, Dict as appropriate, but prioritize more modern use of |, list, and dict without imports

### Imports
- Group imports: standard library, third-party, local
- Use absolute imports (e.g., `from crittercam.pipeline.ingest import func` not `from .ingest import func`)
- Sort imports alphabetically within groups
- Avoid wildcard imports

### Code Formatting
- Line length: 99 characters
- Use 4 spaces for indentation
- Follow PEP 8 conventions
- Use meaningful variable names
- Use idx for index
- Use adjectives after nouns, such as idx_train and idx_test rather than train_idx and test_idx
- Include newline at the end of every .py file
- Do not allow trailing whitespace
- Do not include whitespace for blank lines
- Use single quotes for strings
- Add a comma to the end of multi-line function arguments:
```python
foo(
    param1,
    param2,
)
```
not
```python
foo(
    param1,
    param2
)
```

### Misc
- Use `pathlib.Path` instead of `os` for path handling

## Pipeline Conventions

### Idempotency
- Every pipeline phase must be safe to re-run without side effects
- Ingestion must not duplicate images already present in the archive
- Processing must not create duplicate detection rows for an already-processed image
- Use database state (not file presence alone) to determine what work remains

### Phase responsibilities
- **Phase 1 — Ingestion**: copy new images from SD card into `images/YYYY/MM/DD/`, log each file in the `images` table, enqueue for processing
- **Phase 2 — Processing**: run the classifier, write detection rows, generate derived assets (thumbnail, crops)
- **Phase 3 — Storage**: schema and migration management; export scripts
- **Phase 4 — Interface**: local web dashboard only; reads from DB and derived asset paths

### Batch processing
- The pipeline is batch-oriented (monthly SD card offload), not streaming
- SQLite bulk inserts should use a single transaction with pragmas relaxed for the write window:
  ```python
  conn.execute('PRAGMA synchronous = OFF')
  conn.execute('PRAGMA journal_mode = MEMORY')
  # ... bulk inserts ...
  conn.execute('PRAGMA synchronous = FULL')
  conn.execute('PRAGMA journal_mode = WAL')
  ```
- Drop indexes before bulk insert, rebuild afterward where appropriate

### Classifier interface
- The classifier is a swappable component isolated behind a clean interface
- All classifiers must conform to this contract:
  ```python
  def classify(image_path: Path) -> list[Detection]:
      """Run detection on a single image.

      Args:
          image_path: path to a JPEG image file

      Returns:
          list of Detection objects, empty if no animals detected
      """
  ```
- `Detection` holds: `label: str`, `confidence: float`, `bbox: tuple[float, float, float, float] | None`
- Pipeline code must never import a specific classifier directly — always call through the interface

## Database Conventions

### Schema principles
- `images` table: one row per image file (path, timestamp, ingestion time, empty frame flag)
- `detections` table: one row per animal per image (foreign key to image, label, confidence, bbox, crop path, human correction fields)
- Corrections are stored as fields on the detection row (e.g., `human_label`, `corrected_at`), never by modifying the original AI-generated fields
- AI-generated labels and human corrections must be clearly distinguishable in every query

### Data integrity
- Raw images in `images/YYYY/MM/DD/` are **never modified or deleted** by any code
- Derived assets in `derived/YYYY/MM/DD/` may be regenerated freely
- All corrections and annotations live in the database

### SQL parameters
- Always use named parameters (`:name`) rather than positional placeholders (`?`) for SQL queries
- Pass parameters as a dict: `conn.execute('... WHERE id = :id', {'id': row_id})`
- Positional `?` is only acceptable for single-parameter queries where the mapping is unambiguous

### Derived assets
- Derived assets (thumbnails, detection crops) are written to disk and referenced by path in the DB — never stored as BLOBs
- Directory structure mirrors the image archive:
  ```
  images/YYYY/MM/DD/<filename>.jpg          # original, immutable
  derived/YYYY/MM/DD/<filename>_thumb.jpg   # full-image thumbnail
  derived/YYYY/MM/DD/<filename>_det001.jpg  # crop for detection 1
  derived/YYYY/MM/DD/<filename>_det002.jpg  # crop for detection 2
  ```
- Crop padding is a configurable parameter (suggested default: 15–20% of bbox dimensions, clamped to image boundary), not a hardcoded constant

## Testing

### Unit Tests
- Use pytest framework
- Test directory structure must mirror the source package structure exactly:
  - `crittercam/pipeline/db.py` → `tests/pipeline/test_db.py`
  - `crittercam/pipeline/exif.py` → `tests/pipeline/test_exif.py`
  - `crittercam/cli.py` → `tests/test_cli.py`
  - Each subdirectory under `tests/` must have an `__init__.py`
- Test file naming: `test_<module_name>.py`
- Test function naming: `test_<scenario>`
- Create test classes for each function
- Use fixtures for common test data; place fixtures in a `conftest.py` in the same directory as the tests that use them
- Test assets (e.g. sample images) live in an `assets/` subdirectory alongside the tests that use them
- Aim for high test coverage
- Test both success and failure cases

### Test Structure
```python
class Test<function_name>:
    """Test the function <function_name>."""

    def test_<function_name>_<scenario>(self):
        # Arrange
        # Act
        # Assert
```

### Mocking
- Use unittest.mock for external dependencies
- Mock at the boundary of your system
- Use dependency injection when possible

## Documentation

### Docstrings
```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """Brief description of function.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: Description of when this exception is raised
    """
```
If there are too many params for a single line, put one param per line, indented four spaces:
```python
def function_name(
    param1: Type1,
    param2: Type2,
    param3: Type3,
    param4: Type4,
) -> ReturnType:
```

### Module Documentation
- Every module should have a module-level docstring
- Describe the purpose and main functionality

## Error Handling

### Exceptions
- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately
- Use try/except blocks judiciously

### Logging
- Use Python's logging module
- Include appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log important events and errors
- Include context in log messages

## Project Structure

### Package Organization
- Keep modules focused and cohesive
- Use clear, descriptive module names
- Group related functionality together
- Avoid circular imports

### Directory layout
```
crittercam/
├── design/
│   ├── DESIGN.md
│   ├── PHASES.md
│   └── DECISIONS.md
├── CLAUDE.md
├── crittercam/
│   ├── cli.py
│   ├── config.py
│   ├── pipeline/       # ingestion + processing code
│   ├── classifier/     # swappable classifier modules
│   └── web/            # dashboard interface
└── tests/
    ├── test_cli.py
    ├── test_config.py
    └── pipeline/       # mirrors crittercam/pipeline/
        ├── assets/     # sample images and other test fixtures
        ├── conftest.py
        ├── test_db.py
        ├── test_exif.py
        └── test_ingest.py
```

### File Naming
- Use snake_case for Python files
- Use descriptive names
- Group related files in subdirectories

## CLI Guidelines

### Command Structure
- Use subcommands for different operations
- Provide clear help messages
- Validate input parameters
- Handle errors gracefully

### Configuration
- Support both command-line arguments and config files
- Use sensible defaults
- Validate configuration before execution

## Dependencies

### Adding Dependencies
- Only add dependencies that are truly needed
- Prefer well-maintained packages
- Do not pin versions
- Update pyproject.toml and document changes

### Version Management
- Use semantic versioning
- Update version in pyproject.toml
- Tag releases appropriately

## Git Workflow

### Commits
- Write clear, descriptive commit messages
- Make atomic commits
- Include tests with feature commits
- Run tests before committing

### Branches
- Use feature branches for development
- Keep branches focused and short-lived
- Merge with pull requests
- Delete merged branches

## Additional Notes

Refer to design/DESIGN.md, design/PHASES.md, and design/DECISIONS.md for architectural
context before making structural changes. When a decision has been logged in DECISIONS.md,
follow it; if you believe it should be revisited, flag it rather than working around it silently.
