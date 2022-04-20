#!python
"""This module allows to create temporary mmapped arrays."""

# builtin
import os
import logging
import atexit
import shutil

# external
import numpy as np
import mmap
import h5py
import tempfile


_TEMP_DIR = tempfile.TemporaryDirectory(prefix="temp_mmap_")
TEMP_DIR_NAME = _TEMP_DIR.name
ARRAYS = []
MMAPS = []
CLOSED = False

logging.warning(
    f"WARNING: Temp mmap arrays are written to {TEMP_DIR_NAME}. "
    "Cleanup of this folder is OS dependant, "
    "and might need to be triggered manually! "
    f"Current space: {shutil.disk_usage(TEMP_DIR_NAME)[-1]}"
)


def empty(shape: tuple, dtype: np.dtype) -> np.ndarray:
    """Create a writable temporary mmapped array.

    Parameters
    ----------
    shape : tuple
        A tuple with the shape of the array.
    dtype : type
        The np.dtype of the array.

    Returns
    -------
    type
        A writable temporary mmapped array.
    """
    *other, free_space = shutil.disk_usage(TEMP_DIR_NAME)
    required_space = np.product(shape) * np.dtype(dtype).itemsize
    if free_space < required_space:
        raise IOError(
            f"Cannot create array of size {required_space} "
            f"(available space on {TEMP_DIR_NAME} is {free_space})."
        )
    temp_file_name = os.path.join(
        TEMP_DIR_NAME,
        f"temp_mmap_{np.random.randint(2**31)}{np.random.randint(2**31)}.hdf"
    )
    with h5py.File(temp_file_name, "w") as hdf_file:
        array = hdf_file.create_dataset(
            "array",
            shape=shape,
            dtype=dtype
        )
        array[0] = 0
        offset = array.id.get_offset()
    with open(temp_file_name, "rb+") as raw_hdf_file:
        mmap_obj = mmap.mmap(
            raw_hdf_file.fileno(),
            0,
            access=mmap.ACCESS_WRITE
        )
        _array = np.frombuffer(
            mmap_obj,
            dtype=dtype,
            count=np.prod(shape),
            offset=offset
        ).reshape(shape)
        ARRAYS.append(_array)
        MMAPS.append(mmap_obj)
        return _array


def zeros(shape: tuple, dtype: np.dtype) -> np.ndarray:
    """Create a writable temporary mmapped array filled with zeros.

    Parameters
    ----------
    shape : tuple
        A tuple with the shape of the array.
    dtype : type
        The np.dtype of the array.

    Returns
    -------
    type
        A writable temporary mmapped array filled with zeros.
    """
    _array = empty(shape, dtype)
    _array[:] = 0
    return _array


def ones(shape: tuple, dtype: np.dtype) -> np.ndarray:
    """Create a writable temporary mmapped array filled with ones.

    Parameters
    ----------
    shape : tuple
        A tuple with the shape of the array.
    dtype : type
        The np.dtype of the array.

    Returns
    -------
    type
        A writable temporary mmapped array filled with ones.
    """
    _array = empty(shape, dtype)
    _array[:] = 1
    return _array


@atexit.register
def atexit_clear() -> str:
    """Reset the temporary folder containing temp mmapped arrays.

    WARNING: All existing temp mmapp arrays will be unusable!

    Returns
    -------
    str
        The name of the new temporary folder.
    """
    global CLOSED
    CLOSED = True
    clear()


def clear() -> str:
    """Reset the temporary folder containing temp mmapped arrays.

    WARNING: All existing temp mmapp arrays will be unusable!

    Returns
    -------
    str
        The name of the new temporary folder.
    """
    global _TEMP_DIR
    global TEMP_DIR_NAME
    global ARRAYS
    global MMAPS
    global CLOSED
    if not CLOSED:
        logging.warning(
            f"Folder {TEMP_DIR_NAME} with temp mmap arrays is being deleted. "
            "All existing temp mmapp arrays will be unusable!"
        )
        CLOSED = True
    for _mmap in MMAPS:
        _mmap.close()
    del _TEMP_DIR
    _TEMP_DIR = tempfile.TemporaryDirectory(prefix="temp_mmap_")
    TEMP_DIR_NAME = _TEMP_DIR.name
    ARRAYS = []
    MMAPS = []
    return TEMP_DIR_NAME
