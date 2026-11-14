from sgp4.api import Satrec

def sgp4_array(self, jd, fr):
    """
    
    Compute positions and velocities for the times in a NumPy array.
    Given NumPy arrays ``jd`` and ``fr`` of the same length that
    supply the whole part and the fractional part of one or more
    Julian dates, return a tuple ``(e, r, v)`` of three vectors:
    * ``e``: nonzero for any dates that produced errors, 0 otherwise.
    * ``r``: position vectors in kilometers.
    * ``v``: velocity vectors in kilometers per second.

    """

    # Import NumPy the first time sgp4_array() is called.

    array = self.array
    if array is None:
        from numpy import array
        Satrec.array = array

    results = [self.sgp4(jd_i, fr_i) for jd_i, fr_i in zip(jd, fr)]
    e, r, v = zip(*results)
    return array(e), array(r), array(v)