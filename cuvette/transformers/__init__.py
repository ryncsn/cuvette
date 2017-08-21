"""
Transformers
"""
from cuvette.utils import find_all_sub_module, load_all_sub_module

__all__ = find_all_sub_module(__file__, exclude=['base'])
Transformers = dict((k, v.Transformer) for k, v in load_all_sub_module(__name__).items())
