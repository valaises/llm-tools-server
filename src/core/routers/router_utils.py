import xattr


def set_file_metadata(file_path, key, value):
    """
    Set custom metadata on a file using extended attributes.

    Args:
        file_path: Path to the file
        key: Metadata key
        value: Metadata value (will be converted to bytes)
    """
    path = str(file_path)
    xattr.setxattr(path, f"user.{key}", str(value).encode('utf-8'))


def get_file_metadata(file_path, key):
    """
    Get custom metadata from a file using extended attributes.

    Args:
        file_path: Path to the file
        key: Metadata key to retrieve

    Returns:
        The metadata value as a string
    """
    path = str(file_path)
    try:
        value = xattr.getxattr(path, f"user.{key}")
        return value.decode('utf-8')
    except (OSError, IOError):
        return None
