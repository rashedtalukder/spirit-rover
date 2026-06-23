# Spirit Rover - Migration Guide

## Summary of Changes

The Spirit Rover codebase has been reorganized from Python 2.7 to Python 3.11+ with a more professional, library-focused structure.

## New Project Structure

```
spirit_pi_code/
├── spirit_rover/              # Main library package (NEW)
│   ├── __init__.py           # Package initialization
│   ├── core.py               # Core hardware interface (was spirit_core.py)
│   ├── pixels.py             # Pixel control (was spirit_pixels.py)
│   └── constants.py          # Configuration constants (NEW)
│
├── examples/                  # Example scripts (NEW ORGANIZATION)
│   ├── sensors/              # Sensor reading examples
│   │   ├── lightsense_ambient.py
│   │   ├── lightsense_surface.py
│   │   ├── rangefinder.py
│   │   └── volts.py
│   ├── movement/             # Motor and servo examples
│   │   ├── motors_forward_backward.py
│   │   ├── motors_spinleft.py
│   │   └── servo_shakehead.py
│   └── pixels/               # LED pixel examples
│       ├── pixel_eyes.py
│       ├── pixel_individual.py
│       └── pixel_autofade_wings.py
│
├── rover/democode/           # Original demo code (LEGACY - kept for reference)
├── setup.py                  # Package installation script (NEW)
└── README.md                 # Comprehensive documentation (NEW)
```

## Key Improvements

### 1. **Proper Python Package Structure**
- Library code is now in `spirit_rover/` package
- Can be installed with `pip3 install -e .`
- Import with: `from spirit_rover import Spirit, PixelController`

### 2. **Separated Library from Examples**
- Core library: `spirit_rover/`
- Example code: `examples/`
- Old demo code preserved in `rover/democode/` for reference

### 3. **Python 3.11+ Compatibility**
- All `print` statements → `print()` functions
- String formatting uses `.format()` method
- Better exception handling with `(IOError, OSError)`
- Proper division operators (`//` for integer division)

### 4. **Improved Code Organization**
- Constants extracted to `constants.py`
- Better error handling and logging
- Proper docstrings for all classes and methods
- Type hints and documentation

### 5. **Better Examples**
- Organized by category (sensors, movement, pixels)
- Include error handling
- Use modern Python patterns
- All executable (`#!/usr/bin/env python3`)

## Migration Steps for Your Code

### Old Way (Python 2.7):
```python
#!/usr/bin/python

import spirit_core
import spirit_pixels as pixels

s = spirit_core.Spirit()
s.i2c_process_delay(15)

# Use motors
s.motors(100, 100)

# Use pixels
pixels.eyes(200, 100)
```

### New Way (Python 3.11+):
```python
#!/usr/bin/env python3

from spirit_rover import Spirit, PixelController

# Initialize
rover = Spirit()
rover.i2c_process_delay(15)
pixels = PixelController()

# Use motors
rover.motors(100, 100)

# Use pixels
pixels.eyes(200, 100)
```

## Installation

### Option 1: Install as Package (Recommended)
```bash
cd /path/to/spirit_pi_code
pip3 install -e .
```

Now you can import from anywhere:
```python
from spirit_rover import Spirit, PixelController
```

### Option 2: Use Directly
Add the library to your Python path:
```python
import sys
sys.path.insert(0, '/path/to/spirit_pi_code')
from spirit_rover import Spirit, PixelController
```

## Breaking Changes

1. **Import paths changed**:
   - `import spirit_core` → `from spirit_rover import Spirit`
   - `import spirit_pixels` → `from spirit_rover import PixelController`

2. **PixelController is now a class**:
   - Old: `pixels.eyes(200, 100)` (module function)
   - New: `pixels = PixelController()` then `pixels.eyes(200, 100)`

3. **Constants moved**:
   - Constants like `PIC_I2C_ADDRESS` now in `spirit_rover.constants`
   - Import with: `from spirit_rover.constants import PIC_I2C_ADDRESS`

## Testing Your Migration

Run the example scripts to verify everything works:

```bash
# Test sensor reading
python3 examples/sensors/lightsense_surface.py

# Test motor control
python3 examples/movement/motors_forward_backward.py

# Test pixel control (requires pixel server running)
python3 examples/pixels/pixel_eyes.py
```

## Benefits of New Structure

1. **Easier to maintain**: Separation of concerns
2. **Easier to extend**: Add new features to library
3. **Easier to distribute**: Standard Python package
4. **Easier to document**: Clear API with docstrings
5. **Easier to test**: Isolated components
6. **Better for projects**: Import as dependency

## Backward Compatibility

The original code in `rover/democode/` has been preserved but updated for Python 3. However, it's recommended to migrate to the new structure for future projects.

## Support

For issues or questions:
1. Check the README.md for API documentation
2. Review examples in `examples/` directory
3. Refer to docstrings in library code
