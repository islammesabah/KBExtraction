# -----------------------------------------------------------------------------
# Utils for our Vector Index implementaion using Facebook AI Similarity Search (FAISS).
# -----------------------------------------------------------------------------
import numpy as np

def _as_float32_matrix(x: np.ndarray, *, name: str) -> np.ndarray:
    """
    Convert an input array to a contiguous 2D NumPy float32 matrix.

    Parameters
    ----------
    x:
        Input array that should represent a matrix of vectors.

    name:
        Human-readable label used in error messages.

    Returns
    -------
    np.ndarray
        Contiguous array of dtype float32 with shape (N, D).

    Raises
    ------
    ValueError
        If the input cannot be interpreted as a 2D matrix.
    """
    arr = np.asarray(x, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError(f"❌ {name} must be a 2D array of shape (N, D). Got shape: {arr.shape}")
    return np.ascontiguousarray(arr, dtype=np.float32)


def _as_float32_vector(x: np.ndarray, *, dim: int, name: str) -> np.ndarray:
    """
    Convert an input array to a contiguous 1D NumPy float32 vector of length `dim`.

    Parameters
    ----------
    x:
        Input array that should represent a single vector.

    dim:
        Expected dimensionality.

    name:
        Human-readable label used in error messages.

    Returns
    -------
    np.ndarray
        Contiguous float32 vector with shape (dim,).

    Raises
    ------
    ValueError
        If the vector does not match the expected dimensionality.
    """
    v = np.asarray(x, dtype=np.float32).reshape(-1) # Flatten to 1D
    if v.shape[0] != dim:
        raise ValueError(f"❌ {name} must have shape ({dim},). Got shape: {v.shape}")
    return np.ascontiguousarray(v, dtype=np.float32)


def _l2_normalize_rows(x: np.ndarray) -> np.ndarray:
    """
    L2-normalize each row in a (N, D) matrix.

    This is used to convert inner product into cosine similarity.

    Parameters
    ----------
    x:
        Matrix of shape (N, D), float32.

    Returns
    -------
    np.ndarray
        Matrix of shape (N, D), float32, where each row has L2 norm 1.0
        (or remains all-zeros if the row was originally all-zeros).

    Notes
    -----
    - If a row is all zeros, its norm is 0; we keep it as zeros to avoid NaNs.
    - This function is deterministic and does not modify the input in-place.
    """
    x = np.asarray(x, dtype=np.float32)
    norms = np.linalg.norm(x, axis=1, keepdims=True) # axis=1 means row-wise
    norms = np.where(norms == 0.0, 1.0, norms) # Avoid division by zero
    
    # Now divide each row by its norm so that each row has L2 norm 1.0 
    return x / norms

