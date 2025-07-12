# MemoryOS_main/__init__.py
# -*- coding: utf-8 -*-
"""
"""


import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
from memoryos.embedders.local_embedder import LocalEmbedder

__all__ = ["LocalEmbedder"]
__version__ = "0.1.0"
__author__ = "Resonant Jones"