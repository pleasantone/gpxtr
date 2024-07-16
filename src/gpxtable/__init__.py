"""
gpxtable - Create a markdown template from a Garmin GPX file for route information
"""

__version__ = "1.5.0"
__all__ = ["GPXTableCalculator"]
__author__ = "Paul Traina"

from .gpxtable import GPXTableCalculator, GPXPointMixin
