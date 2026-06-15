"""
Cross-platform data path configuration
Supports Windows (D: drive), Linux (/mnt), and macOS (~/)
"""

from pathlib import Path
import os
import platform
import logging

logger = logging.getLogger(__name__)


def get_data_path() -> Path:
    """
    Get platform-independent data path.

    Priority:
    1. Environment variable AVM_DATA_PATH
    2. Windows: D:\\LG_AVM_Workspace_Data_Moved_20260604
    3. Linux: /mnt/avm_data
    4. macOS: ~/avm_data

    Returns:
        Path: Valid data directory path

    Raises:
        RuntimeError: If path cannot be created or accessed
    """

    # 1. Check environment variable
    env_path = os.getenv('AVM_DATA_PATH')
    if env_path:
        data_path = Path(env_path)
        if data_path.exists():
            logger.info(f"Using AVM_DATA_PATH from environment: {data_path}")
            return data_path

    # 2. Platform-specific defaults
    system = platform.system()

    if system == 'Windows':
        default_path = Path(r'D:\LG_AVM_Workspace_Data_Moved_20260604')
        logger.info(f"Windows detected: using {default_path}")
    elif system == 'Linux':
        default_path = Path('/mnt/avm_data')
        logger.info(f"Linux detected: using {default_path}")
    elif system == 'Darwin':  # macOS
        default_path = Path.home() / 'avm_data'
        logger.info(f"macOS detected: using {default_path}")
    else:
        default_path = Path('./avm_data')
        logger.warning(f"Unknown system {system}: using fallback {default_path}")

    # 3. Create path if it doesn't exist
    if not default_path.exists():
        try:
            default_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created data path: {default_path}")
        except PermissionError:
            logger.error(f"Permission denied: cannot create {default_path}")
            raise RuntimeError(f"Cannot create data path {default_path}: Permission denied")
        except Exception as e:
            logger.error(f"Failed to create {default_path}: {e}")
            raise RuntimeError(f"Cannot create data path {default_path}: {e}")

    return default_path


def get_subpath(relative_path: str) -> Path:
    """
    Get or create a sub-path within the data directory.

    Args:
        relative_path (str): Relative path (e.g., 'Raw_Data', 'Cleansed_Data')

    Returns:
        Path: Full path to the sub-directory
    """

    base = get_data_path()
    subpath = base / relative_path

    if not subpath.exists():
        try:
            subpath.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created sub-path: {subpath}")
        except Exception as e:
            logger.error(f"Failed to create {subpath}: {e}")
            raise RuntimeError(f"Cannot create sub-path {subpath}: {e}")

    return subpath


def get_models_path() -> Path:
    """
    Get models directory path.

    Returns:
        Path: Models directory
    """
    env_path = os.getenv('AVM_MODELS_PATH')
    if env_path:
        models_path = Path(env_path)
    else:
        models_path = Path(__file__).parent.parent / 'models'

    models_path.mkdir(parents=True, exist_ok=True)
    return models_path


def validate_paths() -> dict:
    """
    Validate all required paths exist and are writable.

    Returns:
        dict: Status of all paths
    """

    paths = {
        'data': get_data_path(),
        'raw_data': get_subpath('Raw_Data'),
        'processed_data': get_subpath('Processed_Data'),
        'indexed_data': get_subpath('Indexed_Data'),
        'cleansed_data': get_subpath('Cleansed_Data'),
        'archived': get_subpath('Archived'),
        'models': get_models_path(),
    }

    status = {}
    for name, path in paths.items():
        try:
            # Check if writable
            test_file = path / '.write_test'
            test_file.touch()
            test_file.unlink()
            status[name] = {'path': str(path), 'exists': True, 'writable': True}
        except Exception as e:
            status[name] = {'path': str(path), 'exists': path.exists(), 'writable': False, 'error': str(e)}

    return status


# Initialize paths on module import
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    paths = validate_paths()
    for name, info in paths.items():
        status = '✅' if info['writable'] else '❌'
        print(f"{status} {name}: {info['path']}")
